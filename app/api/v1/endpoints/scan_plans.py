from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import models
from app.db.session import get_db
from app.schemas.scan_plan import (
    ScanPlanCreate,
    ScanPlanInDB,
    ScanPlanUpdate,
    ScanPlanToolConfig,
)

router = APIRouter()


def ensure_default_scan_plan(db: Session) -> None:
    """
    确保默认扫描方案存在，如果不存在则创建
    如果已存在，检查并更新工具配置（确保包含所有内置工具）
    """
    default_plan_name = "默认扫描方案"
    existing = db.query(models.ScanPlan).filter(models.ScanPlan.name == default_plan_name).first()
    
    # 获取所有内置工具（确保工具已初始化）
    # 注意：这里需要先确保工具已初始化，所以需要调用工具列表接口的逻辑
    # 但为了避免循环依赖，我们直接查询数据库
    builtin_tools = db.query(models.Tool).filter(models.Tool.is_builtin == True).all()
    builtin_tool_names = {tool.name for tool in builtin_tools}
    
    if existing:
        # 如果方案已存在，检查并更新工具配置
        existing_tools = db.query(models.ScanPlanTool).filter(
            models.ScanPlanTool.scan_plan_id == existing.id
        ).all()
        existing_tool_names = {t.tool_name for t in existing_tools}
        
        # 添加缺失的工具
        for tool in builtin_tools:
            if tool.name not in existing_tool_names:
                config = {}
                if tool.command_template:
                    config["command_template"] = tool.command_template
                db.add(
                    models.ScanPlanTool(
                        scan_plan_id=existing.id,
                        tool_name=tool.name,
                        enabled=True,
                        config=config,
                    )
                )
        
        # 删除不存在的工具（如果工具被删除）
        for tool in existing_tools:
            if tool.tool_name not in builtin_tool_names:
                db.delete(tool)
        
        db.commit()
        return
    
    # 创建默认扫描方案
    plan = models.ScanPlan(
        name=default_plan_name,
        description="系统默认扫描方案，包含所有内置工具的默认命令配置",
        options={},
    )
    db.add(plan)
    db.flush()
    
    # 为每个内置工具创建配置，使用工具的默认命令模板
    for tool in builtin_tools:
        config = {}
        if tool.command_template:
            config["command_template"] = tool.command_template
        
        db.add(
            models.ScanPlanTool(
                scan_plan_id=plan.id,
                tool_name=tool.name,
                enabled=True,
                config=config,
            )
        )
    
    db.commit()


@router.get("", response_model=List[ScanPlanInDB])
def list_scan_plans(
    *,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    """
    列出所有掃描方案。
    暫不做租戶切分，後續如有需要可加上 tenant 維度。
    首次调用时会自动创建默认扫描方案。
    """
    # 确保默认扫描方案存在
    ensure_default_scan_plan(db)
    
    # 使用 joinedload 预加载 tools 关系，确保返回的数据包含工具配置
    from sqlalchemy.orm import joinedload
    plans = db.query(models.ScanPlan).options(joinedload(models.ScanPlan.tools)).order_by(models.ScanPlan.id.desc()).all()
    return plans


@router.post("", response_model=ScanPlanInDB, status_code=status.HTTP_201_CREATED)
def create_scan_plan(
    *,
    db: Session = Depends(get_db),
    plan_in: ScanPlanCreate,
    _: models.User = Depends(get_current_user),
):
    """
    創建新的掃描方案，並關聯方案中的工具配置。
    """
    existing = db.query(models.ScanPlan).filter(models.ScanPlan.name == plan_in.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="掃描方案名稱已存在",
        )

    plan = models.ScanPlan(
        name=plan_in.name,
        description=plan_in.description,
        options=plan_in.options or {},
    )
    db.add(plan)
    db.flush()

    for tool in plan_in.tools:
        db.add(
            models.ScanPlanTool(
                scan_plan_id=plan.id,
                tool_name=tool.tool_name,
                enabled=tool.enabled,
                config=tool.config or {},
            )
        )

    db.commit()
    db.refresh(plan)
    # 重新加载 tools 关系，确保返回的数据包含最新的工具配置
    from sqlalchemy.orm import joinedload
    plan = db.query(models.ScanPlan).options(joinedload(models.ScanPlan.tools)).filter(models.ScanPlan.id == plan.id).first()
    return plan


@router.put("/{plan_id}", response_model=ScanPlanInDB)
def update_scan_plan(
    *,
    db: Session = Depends(get_db),
    plan_id: int,
    plan_in: ScanPlanUpdate,
    _: models.User = Depends(get_current_user),
):
    """
    更新掃描方案的基本信息與工具配置。
    """
    plan = db.query(models.ScanPlan).filter(models.ScanPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="掃描方案不存在",
        )

    if plan_in.description is not None:
        plan.description = plan_in.description
    if plan_in.options is not None:
        plan.options = plan_in.options

    # 更新工具配置：先刪後插的簡單實現
    if plan_in.tools is not None:
        db.query(models.ScanPlanTool).filter(
            models.ScanPlanTool.scan_plan_id == plan_id
        ).delete()
        db.flush()
        for tool in plan_in.tools:
            db.add(
                models.ScanPlanTool(
                    scan_plan_id=plan_id,
                    tool_name=tool.tool_name,
                    enabled=tool.enabled,
                    config=tool.config or {},
                )
            )

    db.commit()
    db.refresh(plan)
    # 重新加载 tools 关系，确保返回的数据包含最新的工具配置
    from sqlalchemy.orm import joinedload
    plan = db.query(models.ScanPlan).options(joinedload(models.ScanPlan.tools)).filter(models.ScanPlan.id == plan_id).first()
    return plan


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scan_plan(
    *,
    db: Session = Depends(get_db),
    plan_id: int,
    _: models.User = Depends(get_current_user),
):
    """
    刪除掃描方案。
    若已有任務關聯該方案，建議在前端限制刪除或在此處增加檢查。
    """
    plan = db.query(models.ScanPlan).filter(models.ScanPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="掃描方案不存在",
        )

    db.query(models.ScanPlanTool).filter(
        models.ScanPlanTool.scan_plan_id == plan_id
    ).delete()
    db.delete(plan)
    db.commit()