from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import ApiCredential, CredentialProvider


class ApiCredentialRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_active(self, tenant_id: int, provider: CredentialProvider) -> Optional[ApiCredential]:
        return (
            self.db.query(ApiCredential)
            .filter(
                ApiCredential.tenant_id == tenant_id,
                ApiCredential.provider == provider,
                ApiCredential.is_active.is_(True),
            )
            .one_or_none()
        )

    def upsert(
        self,
        tenant_id: int,
        provider: CredentialProvider,
        api_key: Optional[str] = None,
        api_email: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> ApiCredential:
        obj = (
            self.db.query(ApiCredential)
            .filter(ApiCredential.tenant_id == tenant_id, ApiCredential.provider == provider)
            .one_or_none()
        )
        if obj is None:
            # 创建新记录
            # api_key 字段在数据库中不能为 NULL，所以必须提供值
            # 如果用户没有提供，使用空字符串（但这种情况应该在前端验证）
            obj = ApiCredential(
                tenant_id=tenant_id,
                provider=provider,
                api_key=api_key if api_key not in [None, ""] else "",
                api_email=api_email,
                is_active=is_active if is_active is not None else True,
            )
        else:
            # 更新现有记录
            # 如果未提供 api_key，保留現有值（避免被 None 或空字符串覆蓋）
            if api_key not in [None, ""]:
                obj.api_key = api_key
            if api_email is not None:
                obj.api_email = api_email
            if is_active is not None:
                obj.is_active = is_active

        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj
