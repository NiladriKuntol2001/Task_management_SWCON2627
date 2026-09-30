"""Create or promote an admin account.

Runs automatically on startup when ADMIN_EMAIL and ADMIN_PASSWORD are set,
and can also be run by hand:

    python -m app.seed admin@example.com "a-strong-password" "Admin Name"
"""
import sys

from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import User
from app.security import hash_password


def ensure_admin(db: Session, email: str, password: str, name: str = "Administrator") -> User:
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(name=name, email=email, hashed_password=hash_password(password), is_admin=True)
        db.add(user)
    else:
        # Promote an existing account; don't overwrite its password on every restart.
        user.is_admin = True
        user.is_active = True
    db.commit()
    db.refresh(user)
    return user


def seed_admin_from_settings() -> None:
    if not (settings.admin_email and settings.admin_password):
        return
    db = SessionLocal()
    try:
        ensure_admin(db, settings.admin_email, settings.admin_password, settings.admin_name)
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print('Usage: python -m app.seed <email> <password> ["Full Name"]')
        sys.exit(1)
    session = SessionLocal()
    try:
        admin = ensure_admin(session, sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "Administrator")
        print(f"Admin ready: {admin.email} (id {admin.id})")
    finally:
        session.close()
