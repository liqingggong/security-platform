from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db import models
from app.db.session import get_db
from app.schemas.fingerprint import (
    FingerprintRuleCreate,
    FingerprintRuleInDB,
    FingerprintRuleUpdate,
)

router = APIRouter()


@router.get("", response_model=List[FingerprintRuleInDB])
def list_fingerprint_rules(
    *,
    db: Session = Depends(get_db),
    _: models.User = Depends(get_current_user),
):
    """
    列出所有指紋規則。
    """
    rules = (
        db.query(models.FingerprintRule)
        .order_by(models.FingerprintRule.created_at.desc())
        .all()
    )
    return rules


@router.post("", response_model=FingerprintRuleInDB, status_code=status.HTTP_201_CREATED)
def create_fingerprint_rule(
    *,
    db: Session = Depends(get_db),
    rule_in: FingerprintRuleCreate,
    _: models.User = Depends(get_current_user),
):
    """
    創建新的指紋規則。
    """
    existing = (
        db.query(models.FingerprintRule)
        .filter(models.FingerprintRule.name == rule_in.name)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="指紋規則名稱已存在",
        )

    rule = models.FingerprintRule(
        name=rule_in.name,
        description=rule_in.description,
        enabled=rule_in.enabled,
        target=rule_in.target,
        pattern=rule_in.pattern,
        meta=rule_in.meta or {},
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.put("/{rule_id}", response_model=FingerprintRuleInDB)
def update_fingerprint_rule(
    *,
    db: Session = Depends(get_db),
    rule_id: int,
    rule_in: FingerprintRuleUpdate,
    _: models.User = Depends(get_current_user),
):
    """
    更新指紋規則。
    """
    rule = (
        db.query(models.FingerprintRule)
        .filter(models.FingerprintRule.id == rule_id)
        .first()
    )
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指紋規則不存在",
        )

    if rule_in.description is not None:
        rule.description = rule_in.description
    if rule_in.enabled is not None:
        rule.enabled = rule_in.enabled
    if rule_in.target is not None:
        rule.target = rule_in.target
    if rule_in.pattern is not None:
        rule.pattern = rule_in.pattern
    if rule_in.meta is not None:
        rule.meta = rule_in.meta

    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_fingerprint_rule(
    *,
    db: Session = Depends(get_db),
    rule_id: int,
    _: models.User = Depends(get_current_user),
):
    """
    刪除指紋規則。
    """
    rule = (
        db.query(models.FingerprintRule)
        .filter(models.FingerprintRule.id == rule_id)
        .first()
    )
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指紋規則不存在",
        )

    db.delete(rule)
    db.commit()


