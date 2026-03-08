from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.db.models import TaskStatus


class TaskCreate(BaseModel):
    name: str
    description: Optional[str] = None
    # 可選關聯掃描方案
    scan_plan_id: Optional[int] = None
    root_domains: Optional[List[str]] = None
    ips: Optional[List[str]] = None
    fofa_query: Optional[str] = None
    hunter_query: Optional[str] = None
    enable: Dict[str, bool] = {
        "fofa": False,
        "hunter": False,
        "subfinder": False,
        "nmap": False,
        "httpx": False,
        "nuclei": False,
    }
    options: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "掃描任務示例",
                "description": "這是一個示例任務",
                "root_domains": ["example.com"],
                "ips": ["1.1.1.1"],
                "fofa_query": "domain=\"example.com\"",
                "enable": {
                    "fofa": True,
                    "subfinder": True,
                    "nmap": False,
                    "httpx": True,
                    "nuclei": False
                },
                "options": {}
            }
        }


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    scan_plan_id: Optional[int] = None
    root_domains: Optional[List[str]] = None
    ips: Optional[List[str]] = None
    fofa_query: Optional[str] = None
    hunter_query: Optional[str] = None
    enable: Optional[Dict[str, bool]] = None
    options: Optional[Dict[str, Any]] = None


class TaskInDB(BaseModel):
    id: int
    name: str
    description: Optional[str]
    status: TaskStatus
    progress: int
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    error: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    tenant_id: int
    scan_plan_id: Optional[int] = None

    class Config:
        from_attributes = True

