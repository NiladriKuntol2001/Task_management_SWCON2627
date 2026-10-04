"""Main administrator (user ID 1) and extra admin accounts.

On every startup the app makes sure user ID 1 exists and is an active admin,
using ADMIN_EMAIL / ADMIN_PASSWORD / ADMIN_NAME (defaults: admin123@gmail.com /
admin@123). It is only *created* once: later restarts never overwrite its
password, so a password changed on the profile page stays changed.

Extra admins can be created or promoted by hand:

    python -m app.seed someone@example.com "a-strong-password" "Full Name"
"""
import sys

from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import ROOT_ADMIN_ID, User
from app.security import hash_password


def ensure_root_admin(db: Session, email: str, password: str, name: str = "Administrator") -> User:
    root = db.get(User, ROOT_ADMIN_ID)
    if root is None:
        clash = db.query(User).filter(User.email == email).first()
        if clash is not None:
            raise RuntimeError(
                f"Cannot create the main admin (ID {ROOT_ADMIN_ID}): {email} is already used by user ID {clash.id}."
            )
        root = User(
            id=ROOT_ADMIN_ID,
            name=name,
            email=email,
            hashed_password=hash_password(password),
            is_admin=True,
            is_active=True,
        )
        db.add(root)
    else:
        root.is_admin = True
        root.is_active = True
    db.commit()
    db.refresh(root)
    return root


def ensure_admin(db: Session, email: str, password: str, name: str = "Administrator") -> User:
    """Create or promote an additional admin account (never ID 1)."""
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(name=name, email=email, hashed_password=hash_password(password), is_admin=True)
        db.add(user)
    else:
        user.is_admin = True
        user.is_active = True
    db.commit()
    db.refresh(user)
    return user


def seed_root_admin_from_settings() -> None:
    db = SessionLocal()
    try:
        ensure_root_admin(db, settings.admin_email, settings.admin_password, settings.admin_name)
    finally:
        db.close()


if __name__ == "__main__":
    session = SessionLocal()
    try:
        if len(sys.argv) == 1:
            admin = ensure_root_admin(session, settings.admin_email, settings.admin_password, settings.admin_name)
        elif len(sys.argv) >= 3:
            admin = ensure_admin(session, sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "Administrator")
        else:
            print('Usage: python -m app.seed                       (ensure main admin, ID 1)')
            print('       python -m app.seed <email> <password> ["Full Name"]   (extra admin)')
            sys.exit(1)
        print(f"Admin ready: {admin.email} (user ID {admin.id})")
    finally:
        session.close()
