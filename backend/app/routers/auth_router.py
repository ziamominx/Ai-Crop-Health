"""Authentication routes: register / login / me / password change."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.security import create_access_token, hash_password, verify_password
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.schemas import (LoginIn, PasswordChange, RegisterIn, TokenOut,
                                 UserOut)
from app.utils.audit import audit

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut, status_code=201)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    if payload.role == "ADMIN":
        raise HTTPException(status_code=403, detail="Admin accounts cannot self-register.")
    if db.query(User).filter(User.email == payload.email.lower()).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    user = User(
        name=payload.name,
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role=payload.role,
        phone=payload.phone,
        language=payload.language,
    )
    db.add(user)
    db.flush()

    audit(db, user.id, "USER_REGISTERED", "user", user.id, {"role": user.role})
    db.commit()
    db.refresh(user)

    token = create_access_token(str(user.id), user.role)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
def login_json(payload: LoginIn, db: Session = Depends(get_db)):
    """JSON login (frontend API client uses this)."""
    return _login(payload.email, payload.password, db)


@router.post("/login-form", response_model=TokenOut, include_in_schema=False)
def login_form(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """OAuth2 form login (Swagger 'Authorize' button)."""
    return _login(form.username, form.password, db)


def _login(email: str, password: str, db: Session) -> TokenOut:
    user = db.query(User).filter(User.email == email.lower()).first()
    if not user or not verify_password(password, user.password_hash):
        audit(db, None, "LOGIN_FAILED", "user", None, {"email": email})
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled.")
    audit(db, user.id, "USER_LOGIN", "user", user.id, {"role": user.role})
    db.commit()
    token = create_access_token(str(user.id), user.role)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(current: User = Depends(get_current_user)):
    return current


@router.post("/change-password", status_code=200)
def change_password(payload: PasswordChange,
                    current: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    if not verify_password(payload.current_password, current.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    current.password_hash = hash_password(payload.new_password)
    audit(db, current.id, "PASSWORD_CHANGED", "user", current.id)
    db.commit()
    return {"detail": "Password updated."}


@router.get("/mode")
def auth_mode():
    """Non-secret runtime mode info for the login screen labels."""
    return {
        "demo_mode": settings.DEMO_MODE,
        "ai_mode": settings.AI_MODE,
        "weather_mode": settings.WEATHER_MODE,
        "demo_farmer_email": settings.DEMO_FARMER_EMAIL if settings.DEMO_MODE else None,
        "demo_officer_email": settings.DEMO_OFFICER_EMAIL if settings.DEMO_MODE else None,
        "demo_admin_email": settings.DEMO_ADMIN_EMAIL if settings.DEMO_MODE else None,
    }
