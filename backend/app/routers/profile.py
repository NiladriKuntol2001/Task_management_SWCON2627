"""Profile: the signed-in user views their account and changes their own
email or password. Every change re-checks the current password."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import ROOT_ADMIN_ID, User
from app.schemas import EmailChange, PasswordChange, UserOut
from app.security import hash_password, verify_password

router = APIRouter(prefix="/profile", tags=["profile"])


def _check_current_password(user: User, current_password: str) -> None:
    if not verify_password(current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your current password is incorrect.",
        )


@router.get("", response_model=UserOut)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/email", response_model=UserOut)
def change_email(
    payload: EmailChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.id == ROOT_ADMIN_ID:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The main administrator's email (user ID 1) is fixed and can't be changed.",
        )
    _check_current_password(current_user, payload.current_password)

    new_email = str(payload.new_email)
    if new_email.lower() == current_user.email.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That is already your email address.",
        )
    if db.query(User).filter(User.email == new_email, User.id != current_user.id).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another account already uses this email.",
        )

    current_user.email = new_email
    db.commit()
    db.refresh(current_user)
    return current_user


@router.put("/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_current_password(current_user, payload.current_password)

    # The new password must not be the same as the previous (current) one.
    if verify_password(payload.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your new password must be different from your current password.",
        )

    current_user.hashed_password = hash_password(payload.new_password)  # NFR-03
    db.commit()
    return None
