from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Account(Base):
    __tablename__ = 'account'

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    picture = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    oauth_provider = Column(String, nullable=True)
    oauth_id = Column(String, nullable=True)

    notes_path = Column(String, unique=True, nullable=True)

    integrations = relationship("Integration", back_populates="account")

    def __repr__(self):
        return f"<Account(id={self.id}, email='{self.email}')>"

class Integration(Base):
    __tablename__ = 'integrations'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('account.id'))
    service = Column(String, nullable=False)
    access_token = Column(String, nullable=True)
    refresh_token = Column(String, nullable=True)
    token_expires_at = Column(String, nullable=True)
    
    # Relationship to Account
    account = relationship("Account", back_populates="integrations")