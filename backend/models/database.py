from sqlalchemy import create_engine, Column, String, Float, Boolean, DateTime, Text, Integer, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bank_analyser.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class AnalysisRecord(Base):
    __tablename__ = "analyses"

    id = Column(String, primary_key=True)
    status = Column(String, default="pending")
    filename = Column(String)
    file_path = Column(String)
    account_info = Column(JSON, nullable=True)
    transactions = Column(JSON, nullable=True)
    analytics = Column(JSON, nullable=True)
    qa_result = Column(JSON, nullable=True)
    raw_text = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)
