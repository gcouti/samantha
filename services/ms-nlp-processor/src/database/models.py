from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=True)
    phone_number = Column(String, unique=True)
    slack_id = Column(String, unique=True)
    oauth_provider = Column(String, nullable=True)
    oauth_id = Column(String, nullable=True)

    auth_token = Column(String, nullable=True)

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"