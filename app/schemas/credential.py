from pydantic import BaseModel
from typing import Optional
from app.db.models import CredentialProvider

class CredentialBase(BaseModel):
    provider: CredentialProvider
    is_active: bool = True

class CredentialCreate(CredentialBase):
    api_key: str
    api_email: Optional[str] = None

class CredentialUpdate(BaseModel):
    api_key: Optional[str] = None
    api_email: Optional[str] = None
    is_active: Optional[bool] = None

class CredentialInDB(CredentialBase):
    id: int
    tenant_id: int
    api_email: Optional[str] = None
    api_key: Optional[str] = None
    
    class Config:
        from_attributes = True
