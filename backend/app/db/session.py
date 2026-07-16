"""Conexão com o MySQL (SQLAlchemy)."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.env import clean_env

DATABASE_URL = clean_env(
    "DATABASE_URL",
    "mysql+pymysql://studyai:studyai_dev_password@localhost:3306/studyai",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
