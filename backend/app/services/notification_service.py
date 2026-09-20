"""Notification service — create in-app notifications."""
from sqlalchemy.orm import Session

from app.models.notification import Notification


def notify(db: Session, user_id: int, ntype: str, title: str, message: str,
           report_id: int | None = None) -> Notification:
    n = Notification(user_id=user_id, report_id=report_id, type=ntype,
                     title=title, message=message)
    db.add(n)
    return n


def notify_officers(db: Session, db_factory, ntype: str, title: str, message: str,
                    report_id: int | None = None) -> int:
    """Send a notification to every active officer. db_factory yields a fresh session
    (used by background tasks)."""
    count = 0
    from app.models.user import User

    with db_factory() as session:
        officers = session.query(User).filter(User.role == "OFFICER", User.is_active.is_(True)).all()
        for officer in officers:
            session.add(Notification(user_id=officer.id, report_id=report_id,
                                     type=ntype, title=title, message=message))
            count += 1
        session.commit()
    return count
