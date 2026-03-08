from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant_id, get_current_user
from app.db import models
from app.db.session import get_db
from app.schemas.credential import CredentialInDB, CredentialUpdate
from app.services.repositories import ApiCredentialRepository

router = APIRouter()


@router.get("", response_model=List[CredentialInDB])
def list_credentials(
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    _: models.User = Depends(get_current_user),
):
    """
    獲取當前租戶的所有API憑證
    """
    repo = ApiCredentialRepository(db)
    return db.query(models.ApiCredential).filter(
        models.ApiCredential.tenant_id == tenant_id
    ).all()


@router.get("/{provider}", response_model=CredentialInDB)
def get_credential(
    provider: models.CredentialProvider,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    _: models.User = Depends(get_current_user),
):
    """
    獲取特定提供者的API憑證
    """
    repo = ApiCredentialRepository(db)
    credential = repo.get_active(tenant_id, provider)
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"未找到 {provider.value} 的憑證",
        )
    return credential


@router.put("/{provider}", response_model=CredentialInDB)
def update_credential(
    provider: models.CredentialProvider,
    credential_in: CredentialUpdate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
    _: models.User = Depends(get_current_user),
):
    """
    更新或創建API憑證
    """
    repo = ApiCredentialRepository(db)
    
    # 檢查是否為FOFA（需要email）
    if provider == models.CredentialProvider.FOFA and not credential_in.api_email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="FOFA憑證需要提供api_email",
        )
    
    # 檢查是否為Hunter（需要api_key，不需要email）
    if provider == models.CredentialProvider.HUNTER:
        # 檢查是否為新創建（需要提供 api_key）
        existing = repo.get_active(tenant_id, provider)
        if not existing and not credential_in.api_key:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Hunter憑證需要提供api_key",
            )
    
    credential = repo.upsert(
        tenant_id=tenant_id,
        provider=provider,
        api_key=credential_in.api_key,
        api_email=credential_in.api_email,
        is_active=credential_in.is_active,
    )
    
    return credential
