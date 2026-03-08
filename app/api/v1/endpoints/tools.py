from typing import List, Optional
import os
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant_id, get_current_user
from app.db import models
from app.db.session import get_db
from app.schemas.tool import ToolCreate, ToolUpdate, ToolInDB
from app.core.config import settings

router = APIRouter()

# 工具文件存储目录
TOOLS_DIR = Path(settings.BASE_DIR) / "tools" / "plugins"
TOOLS_DIR.mkdir(parents=True, exist_ok=True)


@router.get("", response_model=List[ToolInDB])
def list_tools(
    *,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    _: models.User = Depends(get_current_user),
):
    """
    列出当前租户的所有工具（包括内置工具和自定义工具）
    """
    # 定义内置工具配置
    builtin_tools_config = [
        {
            "name": "fofa",
            "display_name": "FOFA",
            "description": "FOFA 资产搜索工具",
            "version": "1.0",
            "tool_type": "api",
            "enabled": True,
            "is_builtin": True,
        },
        {
            "name": "hunter",
            "display_name": "Hunter",
            "description": "Hunter 资产搜索工具",
            "version": "1.0",
            "tool_type": "api",
            "enabled": True,
            "is_builtin": True,
        },
        {
            "name": "subfinder",
            "display_name": "Subfinder",
            "description": "子域名枚举工具",
            "version": "1.0",
            "tool_type": "script",
            "command_template": "subfinder -d {domain} -silent",
            "enabled": True,
            "is_builtin": True,
        },
        {
            "name": "nmap",
            "display_name": "Nmap",
            "description": "端口扫描工具",
            "version": "1.0",
            "tool_type": "binary",
            "command_template": "nmap -sV -p {ports} -oX - {targets}",
            "enabled": True,
            "is_builtin": True,
        },
        {
            "name": "httpx",
            "display_name": "HTTPX",
            "description": "HTTP 存活检测工具",
            "version": "1.0",
            "tool_type": "binary",
            "command_template": "httpx -json -silent -no-color",
            "enabled": True,
            "is_builtin": True,
        },
        {
            "name": "nuclei",
            "display_name": "Nuclei",
            "description": "漏洞扫描工具",
            "version": "1.0",
            "tool_type": "binary",
            "command_template": "nuclei -jsonl -silent {targets}",
            "enabled": True,
            "is_builtin": True,
        },
        {
            "name": "naabu",
            "display_name": "Naabu",
            "description": "端口扫描工具",
            "version": "1.0",
            "tool_type": "binary",
            "command_template": "naabu -host {targets} -json -silent",
            "enabled": True,
            "is_builtin": True,
        },
    ]
    
    # 获取数据库中已有的所有工具
    existing_tools = db.query(models.Tool).filter(models.Tool.tenant_id == tenant_id).all()
    existing_tool_names = {tool.name for tool in existing_tools}
    
    # 确保所有内置工具都存在，如果不存在则创建
    builtin_tool_names = {config["name"] for config in builtin_tools_config}
    for builtin_config in builtin_tools_config:
        if builtin_config["name"] not in existing_tool_names:
            # 创建内置工具记录
            builtin_tool = models.Tool(
                name=builtin_config["name"],
                display_name=builtin_config["display_name"],
                description=builtin_config["description"],
                version=builtin_config["version"],
                tool_type=builtin_config["tool_type"],
                command_template=builtin_config.get("command_template"),
                enabled=builtin_config["enabled"],
                is_builtin=True,
                tenant_id=tenant_id,
                config={},
            )
            db.add(builtin_tool)
    
    db.commit()
    
    # 重新查询所有工具（包括新创建的）
    all_tools = db.query(models.Tool).filter(models.Tool.tenant_id == tenant_id).all()
    
    # 按名称去重（以防万一）
    seen_names = set()
    unique_tools = []
    for tool in all_tools:
        if tool.name not in seen_names:
            seen_names.add(tool.name)
            unique_tools.append(tool)
    
    return unique_tools


@router.get("/{tool_id}", response_model=ToolInDB)
def get_tool(
    *,
    db: Session = Depends(get_db),
    tool_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    _: models.User = Depends(get_current_user),
):
    """
    获取特定工具的详细信息
    """
    tool = (
        db.query(models.Tool)
        .filter(models.Tool.id == tool_id, models.Tool.tenant_id == tenant_id)
        .first()
    )

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="工具不存在",
        )

    return tool


@router.post("", response_model=ToolInDB)
async def create_tool(
    *,
    db: Session = Depends(get_db),
    name: str = Form(...),
    display_name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    version: Optional[str] = Form(None),
    author: Optional[str] = Form(None),
    tool_type: str = Form("script"),
    command_template: Optional[str] = Form(None),
    enabled: bool = Form(True),
    file: Optional[UploadFile] = File(None),
    tenant_id: int = Depends(get_current_tenant_id),
    _: models.User = Depends(get_current_user),
):
    """
    创建新工具（支持文件上传）
    """
    # 检查工具名称是否已存在
    existing_tool = (
        db.query(models.Tool)
        .filter(models.Tool.name == name, models.Tool.tenant_id == tenant_id)
        .first()
    )
    if existing_tool:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="工具名称已存在",
        )

    # 保存上传的文件
    file_path = None
    if file and file.filename:
        # 为每个租户创建独立的目录
        tenant_tools_dir = TOOLS_DIR / str(tenant_id)
        tenant_tools_dir.mkdir(parents=True, exist_ok=True)

        # 保存文件
        safe_filename = f"{name}_{file.filename}"
        file_full_path = tenant_tools_dir / safe_filename
        
        with open(file_full_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 保存相对路径
        file_path = f"{tenant_id}/{safe_filename}"

    # 创建工具记录
    tool = models.Tool(
        name=name,
        display_name=display_name or name,
        description=description,
        version=version,
        author=author,
        tool_type=tool_type,
        file_path=file_path,
        command_template=command_template,
        config={},
        enabled=enabled,
        is_builtin=False,
        tenant_id=tenant_id,
    )

    db.add(tool)
    db.commit()
    db.refresh(tool)

    return tool


@router.put("/{tool_id}", response_model=ToolInDB)
def update_tool(
    *,
    db: Session = Depends(get_db),
    tool_id: int,
    tool_in: ToolUpdate,
    tenant_id: int = Depends(get_current_tenant_id),
    _: models.User = Depends(get_current_user),
):
    """
    更新工具信息
    """
    tool = (
        db.query(models.Tool)
        .filter(models.Tool.id == tool_id, models.Tool.tenant_id == tenant_id)
        .first()
    )

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="工具不存在",
        )

    # 不允许修改内置工具
    if tool.is_builtin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="内置工具不允许修改",
        )

    # 更新字段
    update_data = tool_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tool, field, value)

    db.commit()
    db.refresh(tool)

    return tool


@router.delete("/{tool_id}")
def delete_tool(
    *,
    db: Session = Depends(get_db),
    tool_id: int,
    tenant_id: int = Depends(get_current_tenant_id),
    _: models.User = Depends(get_current_user),
):
    """
    删除工具
    """
    tool = (
        db.query(models.Tool)
        .filter(models.Tool.id == tool_id, models.Tool.tenant_id == tenant_id)
        .first()
    )

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="工具不存在",
        )

    # 不允许删除内置工具
    if tool.is_builtin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="内置工具不允许删除",
        )

    # 删除关联的文件
    if tool.file_path:
        file_full_path = TOOLS_DIR / tool.file_path
        if file_full_path.exists():
            file_full_path.unlink()

    db.delete(tool)
    db.commit()

    return {"message": "工具删除成功"}


@router.post("/{tool_id}/toggle", response_model=ToolInDB)
def toggle_tool(
    *,
    db: Session = Depends(get_db),
    tool_id: int,
    enabled: bool,
    tenant_id: int = Depends(get_current_tenant_id),
    _: models.User = Depends(get_current_user),
):
    """
    启用/禁用工具
    """
    tool = (
        db.query(models.Tool)
        .filter(models.Tool.id == tool_id, models.Tool.tenant_id == tenant_id)
        .first()
    )

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="工具不存在",
        )

    tool.enabled = enabled
    db.commit()
    db.refresh(tool)

    return tool

