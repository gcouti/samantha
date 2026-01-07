from sqlalchemy.orm import Session
from .models import Account
from typing import Optional

def get_user_by_email(db: Session, email: str) -> Optional[Account]:
    """
    Retrieve a user from the database by email.
    """
    return db.query(Account).filter(Account.email == email).first()

def update_user_notes_path(db: Session, email: str, notes_path: str) -> Optional[Account]:
    """
    Update the notes_path for a user.
    """
    user = db.query(Account).filter(Account.email == email).first()
    if user:
        user.notes_path = notes_path
        db.commit()
        db.refresh(user)
        return user
    return None
