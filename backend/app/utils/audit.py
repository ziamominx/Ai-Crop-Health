"""Audit trail helper — record important actions."""
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def audit(db: Session, user_id: int | None, action: str,
          entity_type: str | None = None, entity_id: int | None = None,
          metadata: dict | None = None) -> None:
    db.add(AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=metadata,
    ))
