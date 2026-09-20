"""FastAPI security dependencies — current user + role-based authorization."""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth.security import decode_token
from app.config import settings
from app.database import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if not payload:
        raise credentials_error
    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_error
    user = db.get(User, int(user_id))
    if not user or not user.is_active:
        raise credentials_error
    return user


def require_roles(*roles: str):
    """Dependency factory: restrict an endpoint to the given roles."""

    def checker(current: User = Depends(get_current_user)) -> User:
        if current.role not in roles:
            raise HTTPException(status_code=403, detail="Not authorized for this action")
        return current

    return checker


# Convenience aliases
farmer_required = require_roles("FARMER")
officer_required = require_roles("OFFICER")
admin_required = require_roles("ADMIN")
staff_required = require_roles("OFFICER", "ADMIN")
any_authenticated = require_roles("FARMER", "OFFICER", "ADMIN")
