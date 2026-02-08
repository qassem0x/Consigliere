import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, ForeignKey, Integer, BigInteger, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    files = relationship("File", back_populates="owner", cascade="all, delete-orphan")
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")


class File(Base):
    __tablename__ = "files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size_bytes = Column(BigInteger)
    row_count = Column(Integer)
    columns = Column(JSONB)  
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="files")
    chats = relationship("Chat", back_populates="file", cascade="all, delete-orphan")
    dossier = relationship("Dossier", back_populates="file", uselist=False, cascade="all, delete-orphan")


class Chat(Base):
    __tablename__ = "chats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    file_id = Column(UUID(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"), nullable=False)
    dossier_id = Column(UUID(as_uuid=True), ForeignKey("dossiers.id", ondelete="SET NULL"), nullable=True)
    
    title = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    dossier = relationship("Dossier", back_populates="chats")
    
    user = relationship("User", back_populates="chats")
    file = relationship("File", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id", ondelete="CASCADE"), nullable=False)
    
    role = Column(String(50), nullable=False) 
    content = Column(Text, nullable=False)
    artifacts = Column(JSONB)  
    # Stores { "type": "python", "code": "..." }
    related_code = Column(JSONB)
    steps = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    chat = relationship("Chat", back_populates="messages")


class Dossier(Base):
    __tablename__ = "dossiers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    file_id = Column(UUID(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    file_type = Column(String(100))
    briefing = Column(Text)
    key_entities = Column(JSONB)       
    recommended_actions = Column(JSONB) 
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    file = relationship("File", back_populates="dossier")
    
    chats = relationship("Chat", back_populates="dossier")