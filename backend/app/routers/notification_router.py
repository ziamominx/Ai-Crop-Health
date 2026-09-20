"""Notifications — list, unread count, mark read."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.notification import Notification
from app.models.user import User
from app.schemas.schemas import NotificationOut

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def my_notifications(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return (db.query(Notification)
              .filter(Notification.user_id == current.id)
              .order_by(Notification.created_at.desc())
              .limit(50).all())


@router.get("/unread-count")
def unread_count(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    count = (db.query(Notification)
               .filter(Notification.user_id == current.id, Notification.is_read.is_(False))
               .count())
    return {"count": count}


@router.post("/{notification_id}/read", status_code=200)
def mark_read(notification_id: int, current: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    n = db.get(Notification, notification_id)
    if not n or n.user_id != current.id:
        raise HTTPException(status_code=404, detail="Notification not found.")
    n.is_read = True
    db.commit()
    return {"detail": "Marked read."}


@router.post("/read-all", status_code=200)
def mark_all_read(current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    (db.query(Notification)
       .filter(Notification.user_id == current.id, Notification.is_read.is_(False))
       .update({"is_read": True}, synchronize_session=False))
    db.commit()
    return {"detail": "All notifications marked read."}
