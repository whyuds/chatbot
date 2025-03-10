from sqlalchemy import create_engine, Column, BigInteger, String, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func

Base = declarative_base()

class Conversation(Base):
    __tablename__ = 'conversations'
    id = Column(BigInteger().with_variant(BigInteger, "sqlite"), primary_key=True, autoincrement=True)
    title = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    messages = relationship('Message', backref='conversation')

class Message(Base):
    __tablename__ = 'messages'
    id = Column(BigInteger().with_variant(BigInteger, "sqlite"), primary_key=True, autoincrement=True)
    conversation_id = Column(BigInteger().with_variant(BigInteger, "sqlite"), ForeignKey('conversations.id'))
    role = Column(String(50))
    content = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

# Database engine and session
engine = create_engine('sqlite:///chat.db')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)