from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant_id, get_current_user
from app.db import models
from app.db.session import get_db
from app.schemas.task import TaskCreate, TaskInDB, TaskUpdate
from app.schemas.scan_plan import TaskLogInDB
from app.workers.tasks import run_pipeline

router = APIRouter()


@router.post("", response_model=TaskInDB, status_code=status.HTTP_201_CREATED)
def create_task(
    *,
    db: Session = Depends(get_db),
    task_in: TaskCreate,
    tenant_id: int = Depends(get_current_tenant_id),
    current_user: models.User = Depends(get_current_user),
):
    """
    創建新的掃描任務
    """
    # 驗證至少啟用了一個工具（如果沒有選擇掃描方案，則必須手動選擇工具）
    if not task_in.scan_plan_id:
        # 沒有選擇掃描方案，必須手動選擇至少一個工具
        if not task_in.enable or not any(task_in.enable.values()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="至少需要啟用一個工具，或選擇一個掃描方案",
            )
    # 如果選擇了掃描方案，工具將由方案自動配置，不需要驗證 enable

    # 驗證輸入參數
    if not task_in.root_domains and not task_in.ips and not task_in.fofa_query and not task_in.hunter_query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="至少需要提供 root_domains、ips、fofa_query 或 hunter_query 其中之一",
        )

    # 驗證掃描方案（如有）並加載工具配置
    plan_tool_configs = {}
    enable_from_plan = {}
    
    if task_in.scan_plan_id:
        plan = (
            db.query(models.ScanPlan)
            .filter(models.ScanPlan.id == task_in.scan_plan_id)
            .first()
        )
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="掃描方案不存在",
            )
        
        # 加載掃描方案中的工具配置
        plan_tools = db.query(models.ScanPlanTool).filter(
            models.ScanPlanTool.scan_plan_id == task_in.scan_plan_id
        ).all()
        
        for plan_tool in plan_tools:
            tool_name = plan_tool.tool_name
            # 構建 plan_tool_configs：{tool_name: config}
            plan_tool_configs[tool_name] = plan_tool.config or {}
            # 構建 enable_from_plan：從掃描方案中獲取哪些工具被啟用
            enable_from_plan[tool_name] = plan_tool.enabled

    # 合併 enable：掃描方案的 enable 優先，如果沒有掃描方案則使用手動選擇的 enable
    final_enable = enable_from_plan if enable_from_plan else (task_in.enable or {})

    # 創建任務記錄
    input_data = {
        "root_domains": task_in.root_domains or [],
        "ips": task_in.ips or [],
        "fofa_query": task_in.fofa_query,
        "hunter_query": task_in.hunter_query,
        "enable": final_enable,
        "options": task_in.options or {},
        "plan_tool_configs": plan_tool_configs,  # 添加掃描方案的工具配置
    }
    
    task = models.Task(
        name=task_in.name,
        description=task_in.description,
        status=models.TaskStatus.PENDING,
        progress=0,
        input_data=input_data,
        scan_plan_id=task_in.scan_plan_id,
        tenant_id=tenant_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # 異步啟動 pipeline
    try:
        run_pipeline.delay(task.id, task.input_data)
    except Exception as e:
        # 如果啟動失敗，更新任務狀態
        task.status = models.TaskStatus.FAILED
        task.error = str(e)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"啟動任務失敗: {str(e)}",
        )

    return task


@router.patch("/{task_id}", response_model=TaskInDB)
def update_task(
    *,
    db: Session = Depends(get_db),
    task_id: int,
    task_in: TaskUpdate,
    tenant_id: int = Depends(get_current_tenant_id),
    _: models.User = Depends(get_current_user),
):
    """
    更新任務：
    - PENDING 狀態：可更新所有字段（名稱、描述、掃描方案、輸入參數、啟用工具、options）
    - 其他狀態：僅可更新名稱和描述（元數據），不允許修改輸入參數
    """
    task = (
        db.query(models.Task)
        .filter(models.Task.id == task_id, models.Task.tenant_id == tenant_id)
        .first()
    )
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任務不存在")
    
    is_pending = task.status == models.TaskStatus.PENDING
    
    # 如果不是 PENDING 狀態，檢查是否嘗試修改輸入參數
    if not is_pending:
        has_input_changes = any([
            task_in.root_domains is not None,
            task_in.ips is not None,
            task_in.fofa_query is not None,
            task_in.hunter_query is not None,
            task_in.enable is not None,
            task_in.options is not None,
            task_in.scan_plan_id is not None,
        ])
        if has_input_changes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="已完成或運行中的任務僅可修改名稱和描述，不允許修改輸入參數或掃描方案",
            )
        # 只允許修改名稱和描述
        if task_in.name is not None:
            task.name = task_in.name
        if task_in.description is not None:
            task.description = task_in.description
        db.commit()
        db.refresh(task)
        return task

    # PENDING 狀態：允許修改所有字段
    # 驗證掃描方案（如有）
    if task_in.scan_plan_id:
        plan_exists = (
            db.query(models.ScanPlan.id)
            .filter(models.ScanPlan.id == task_in.scan_plan_id)
            .first()
        )
        if not plan_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="掃描方案不存在",
            )

    # 若修改輸入參數，確保至少有一項
    any_input = any(
        [
          task_in.root_domains,
          task_in.ips,
          task_in.fofa_query is not None,
          task_in.hunter_query is not None,
        ]
    )
    if any_input:
        root_domains = task_in.root_domains if task_in.root_domains is not None else task.input_data.get("root_domains", [])
        ips = task_in.ips if task_in.ips is not None else task.input_data.get("ips", [])
        fofa_query = task_in.fofa_query if task_in.fofa_query is not None else task.input_data.get("fofa_query")
        hunter_query = task_in.hunter_query if task_in.hunter_query is not None else task.input_data.get("hunter_query")
        if not root_domains and not ips and not fofa_query and not hunter_query:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="至少需要提供 root_domains、ips、fofa_query 或 hunter_query 其中之一",
            )

    if task_in.name is not None:
        task.name = task_in.name
    if task_in.description is not None:
        task.description = task_in.description
    if task_in.scan_plan_id is not None:
        task.scan_plan_id = task_in.scan_plan_id

    # 更新 input_data
    input_data = task.input_data or {}
    if task_in.root_domains is not None:
        input_data["root_domains"] = task_in.root_domains
    if task_in.ips is not None:
        input_data["ips"] = task_in.ips
    if task_in.fofa_query is not None:
        input_data["fofa_query"] = task_in.fofa_query
    if task_in.hunter_query is not None:
        input_data["hunter_query"] = task_in.hunter_query
    if task_in.enable is not None:
        input_data["enable"] = task_in.enable
    if task_in.options is not None:
        input_data["options"] = task_in.options

    task.input_data = input_data
    db.commit()
    db.refresh(task)
    return task


@router.get("", response_model=List[TaskInDB])
def list_tasks(
    *,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[models.TaskStatus] = None,
    tenant_id: int = Depends(get_current_tenant_id),
    _: models.User = Depends(get_current_user),
):
    """
    列出當前租戶的所有任務
    """
    query = db.query(models.Task).filter(models.Task.tenant_id == tenant_id)

    if status:
        query = query.filter(models.Task.status == status)

    tasks = query.order_by(models.Task.created_at.desc()).offset(skip).limit(limit).all()
    return tasks


@router.get("/{task_id}/logs", response_model=List[TaskLogInDB])
def list_task_logs(
    *,
    db: Session = Depends(get_db),
    task_id: int,
    phase: Optional[str] = Query(None),
    _: int = Depends(get_current_tenant_id),
    __: models.User = Depends(get_current_user),
):
    """
    按任務ID獲取執行日誌，可按 phase 過濾。
    """
    query = db.query(models.TaskLog).filter(models.TaskLog.task_id == task_id)
    if phase:
        query = query.filter(models.TaskLog.phase == phase)
    logs = query.order_by(models.TaskLog.created_at.asc()).all()
    return logs


@router.get("/{task_id}", response_model=TaskInDB)
def get_task(
    *,
    db: Session = Depends(get_db),
    task_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    _: models.User = Depends(get_current_user),
):
    """
    獲取特定任務的詳細信息
    """
    task = (
        db.query(models.Task)
        .filter(models.Task.id == task_id, models.Task.tenant_id == tenant_id)
        .first()
    )

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任務不存在",
        )

    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_task(
    *,
    db: Session = Depends(get_db),
    task_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    _: models.User = Depends(get_current_user),
):
    """
    取消任務（僅限 PENDING 或 RUNNING 狀態）
    同時取消 Celery 中的相關任務
    """
    from app.workers.celery_app import celery_app
    from celery.result import AsyncResult
    
    task = (
        db.query(models.Task)
        .filter(models.Task.id == task_id, models.Task.tenant_id == tenant_id)
        .first()
    )

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任務不存在",
        )

    if task.status not in [models.TaskStatus.PENDING, models.TaskStatus.RUNNING]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只能取消 PENDING 或 RUNNING 狀態的任務",
        )

    # 取消 Celery 中的相關任務
    # 從 output_data 中獲取子任務 ID
    output_data = task.output_data or {}
    child_task_ids = output_data.get("child_task_ids", {})
    
    all_child_ids = []
    for ids in child_task_ids.values():
        if isinstance(ids, list):
            all_child_ids.extend([x for x in ids if isinstance(x, str)])
    
    # 取消所有子任務
    for child_id in all_child_ids:
        try:
            r = AsyncResult(child_id, app=celery_app)
            state = r.state
            if state == 'PENDING':
                # 任務還在等待，使用 terminate=False 避免觸發執行
                r.revoke(terminate=False)
            elif state in ['STARTED', 'RETRY']:
                # 任務正在執行，使用 terminate=True 強制終止
                r.revoke(terminate=True)
            # 如果任務已經完成（SUCCESS/FAILURE），不需要取消
        except Exception as e:
            # 如果取消失敗（任務可能已完成），記錄但不影響主流程
            pass
    
    # 取消主 pipeline 任務（如果存在）
    # 注意：主 pipeline 任務的 ID 可能不在 child_task_ids 中，需要從其他地方獲取
    # 這裡我們先更新數據庫狀態，讓任務在執行時檢查狀態
    
    task.status = models.TaskStatus.CANCELLED
    db.commit()

    return None


@router.delete("/{task_id}/hard", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    *,
    db: Session = Depends(get_db),
    task_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    _: models.User = Depends(get_current_user),
):
    """
    硬刪除任務：刪除任務及其相關的資產、漏洞、日誌、來源資產表。
    
    注意：對於聚合表 Asset，使用 last_seen 時間範圍來判斷資產是否屬於該任務。
    如果資產的 last_seen 在任務開始時間之後，則認為是該任務發現的資產，會被刪除。
    """
    task = (
        db.query(models.Task)
        .filter(models.Task.id == task_id, models.Task.tenant_id == tenant_id)
        .first()
    )
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="任務不存在",
        )

    # 刪除關聯的來源資產表（FofaAsset、HunterAsset、SubfinderAsset）
    db.query(models.FofaAsset).filter(models.FofaAsset.task_id == task_id).delete()
    db.query(models.HunterAsset).filter(models.HunterAsset.task_id == task_id).delete()
    db.query(models.SubfinderAsset).filter(models.SubfinderAsset.task_id == task_id).delete()
    
    # 刪除關聯的 TaskLog、Vulnerability
    db.query(models.TaskLog).filter(models.TaskLog.task_id == task_id).delete()
    db.query(models.Vulnerability).filter(models.Vulnerability.task_id == task_id).delete()
    
    # 刪除關聯的 Asset
    # 策略：只刪除 task_id 明確匹配的資產
    # 注意：由於資產可能被多個任務共享（task_id 可能是其他任務的ID），
    # 這裡只刪除 task_id 明確匹配的資產，避免誤刪其他任務的資產
    # 如果資產的 task_id 是其他任務的ID，則不會被刪除（這是預期的，因為資產可能屬於多個任務）
    db.query(models.Asset).filter(
        models.Asset.tenant_id == tenant_id,
        models.Asset.task_id == task_id
    ).delete()

    # 刪除關聯的 Domain 相關表（注意外鍵約束順序）
    # DomainEndpoint 沒有 task_id，需要通過 DomainIP 關聯刪除
    # 1. 先獲取該任務的所有 Domain IDs
    domain_ids = [
        row[0] for row in
        db.query(models.Domain.id).filter(models.Domain.task_id == task_id).all()
    ]
    # 2. 獲取這些 Domain 對應的所有 DomainIP IDs
    if domain_ids:
        domain_ip_ids = [
            row[0] for row in
            db.query(models.DomainIP.id).filter(models.DomainIP.domain_id.in_(domain_ids)).all()
        ]
        # 3. 先刪除 DomainEndpoint（依賴 DomainIP）
        if domain_ip_ids:
            db.query(models.DomainEndpoint).filter(
                models.DomainEndpoint.domain_ip_id.in_(domain_ip_ids)
            ).delete(synchronize_session=False)
        # 4. 再刪除 DomainIP（依賴 Domain）
        db.query(models.DomainIP).filter(models.DomainIP.task_id == task_id).delete()
    # 5. 最後刪除 Domain
    db.query(models.Domain).filter(models.Domain.task_id == task_id).delete()

    db.delete(task)
    db.commit()
    return None

