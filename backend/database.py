from __future__ import annotations

import os

from sqlmodel import Session, SQLModel, create_engine

# Import all models so SQLModel registers their tables
import models.auth
import models.report_record
import models.soap_record
import models.therapy_plan_record  # noqa: F401

DATABASE_URL: str = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL") or "sqlite:///./reports.db"

# Neon uses postgres:// — SQLAlchemy requires postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_db():
    with Session(engine) as session:
        yield session
