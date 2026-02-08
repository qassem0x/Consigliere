import uuid
from sqlalchemy import (
    Column,
    String,
    Boolean,
    ForeignKey,
    Integer,
    BigInteger,
    Text,
    DateTime,
    CheckConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func, text
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100))
    is_active = Column(Boolean, server_default=text("true"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    files = relationship("File", back_populates="owner", cascade="all, delete-orphan")
    connections = relationship(
        "Connection", back_populates="owner", cascade="all, delete-orphan"
    )
    chats = relationship("Chat", back_populates="user", cascade="all, delete-orphan")


class File(Base):
    __tablename__ = "files"

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size_bytes = Column(BigInteger)
    row_count = Column(Integer)
    columns = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="files")
    chats = relationship("Chat", back_populates="file", cascade="all, delete-orphan")
    dossier = relationship(
        "Dossier", back_populates="file", uselist=False, cascade="all, delete-orphan"
    )


class Connection(Base):
    __tablename__ = "connections"

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = Column(String(50), nullable=False)
    engine = Column(String(20), nullable=False)
    connection_string = Column(Text, nullable=False)
    schema = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="connections")
    chats = relationship(
        "Chat", back_populates="connection", cascade="all, delete-orphan"
    )
    dossier = relationship(
        "Dossier",
        back_populates="connection",
        uselist=False,
        cascade="all, delete-orphan",
    )


class Dossier(Base):
    __tablename__ = "dossiers"

    __table_args__ = (
        CheckConstraint(
            "(file_id IS NOT NULL AND connection_id IS NULL) OR (file_id IS NULL AND connection_id IS NOT NULL)",
            name="one_source_only",
        ),
    )

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )

    file_id = Column(
        UUID(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"), nullable=True
    )
    connection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("connections.id", ondelete="CASCADE"),
        nullable=True,
    )

    briefing = Column(Text)
    key_entities = Column(JSONB)
    recommended_actions = Column(JSONB)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    file = relationship("File", back_populates="dossier")
    connection = relationship("Connection", back_populates="dossier")
    chats = relationship("Chat", back_populates="dossier")


class Chat(Base):
    __tablename__ = "chats"

    __table_args__ = (
        CheckConstraint(
            "(file_id IS NOT NULL AND connection_id IS NULL) OR (file_id IS NULL AND connection_id IS NOT NULL)",
            name="chat_source_check",
        ),
    )

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    file_id = Column(
        UUID(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"), nullable=True
    )
    connection_id = Column(
        UUID(as_uuid=True),
        ForeignKey("connections.id", ondelete="CASCADE"),
        nullable=True,
    )

    dossier_id = Column(
        UUID(as_uuid=True),
        ForeignKey("dossiers.id", ondelete="SET NULL"),
        nullable=True,
    )

    title = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", back_populates="chats")
    file = relationship("File", back_populates="chats")
    connection = relationship("Connection", back_populates="chats")
    dossier = relationship("Dossier", back_populates="chats")
    messages = relationship(
        "Message", back_populates="chat", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")
    )
    chat_id = Column(
        UUID(as_uuid=True),
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    artifacts = Column(JSONB)
    related_code = Column(JSONB)
    steps = Column(JSONB)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    chat = relationship("Chat", back_populates="messages")
