from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base

class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String(50), nullable=False)  # 'whatsapp', 'google_meet', etc.
    name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default="uploaded")  # 'uploaded', 'parsed', 'stored', 'indexed', 'ready'
    message_count = Column(Integer, default=0)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    conversations = relationship("Conversation", back_populates="source", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="source", cascade="all, delete-orphan")

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    title = Column(String(255), nullable=True)

    # Relationships
    source = relationship("Source", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    sender = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=False)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id", ondelete="CASCADE"), nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow)
    report_data = Column(Text, nullable=False)  # JSON-serialized report details

    # Relationships
    source = relationship("Source", back_populates="reports")
