from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class ToolCreate(BaseModel):
    """创建工具"""
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    author: Optional[str] = None
    tool_type: str = "script"  # script, binary, docker
    command_template: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    enabled: bool = True


class ToolUpdate(BaseModel):
    """更新工具"""
    display_name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    author: Optional[str] = None
    command_template: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    enabled: Optional[bool] = None


class ToolInDB(BaseModel):
    """工具响应"""
    id: int
    name: str
    display_name: Optional[str]
    description: Optional[str]
    version: Optional[str]
    author: Optional[str]
    tool_type: str
    file_path: Optional[str]
    command_template: Optional[str]
    config: Dict[str, Any]
    enabled: bool
    is_builtin: bool
    created_at: datetime
    updated_at: datetime
    tenant_id: int

    class Config:
        from_attributes = True

