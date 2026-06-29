from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, create_engine, func, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sessions: Mapped[list["AnalysisSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class AnalysisSession(Base):
    __tablename__ = "analysis_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    resume_filename: Mapped[str] = mapped_column(String(255))
    resume_storage_path: Mapped[str] = mapped_column(String(500))
    job_title: Mapped[str] = mapped_column(String(255), default="Untitled role")
    resume_text: Mapped[str] = mapped_column(Text)
    jd_text: Mapped[str] = mapped_column(Text)
    parsed_resume: Mapped[dict] = mapped_column(JSON)
    parsed_jd: Mapped[dict] = mapped_column(JSON)
    match_result: Mapped[dict] = mapped_column(JSON)
    interview_plan: Mapped[dict] = mapped_column(JSON)
    feedback_report: Mapped[dict] = mapped_column(JSON)
    pipeline_stage: Mapped[str] = mapped_column(String(40), default="new", server_default="new")
    reviewer_notes: Mapped[str] = mapped_column(Text, default="", server_default="")
    decision_memo: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="sessions")
    chunks: Mapped[list["EvidenceChunk"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="EvidenceChunk.ordinal"
    )
    activity_events: Mapped[list["ActivityEvent"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="desc(ActivityEvent.created_at)",
    )


class EvidenceChunk(Base):
    __tablename__ = "evidence_chunks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("analysis_sessions.id"), index=True)
    source: Mapped[str] = mapped_column(String(30))
    ordinal: Mapped[int] = mapped_column()
    text: Mapped[str] = mapped_column(Text)

    session: Mapped[AnalysisSession] = relationship(back_populates="chunks")


class ActivityEvent(Base):
    __tablename__ = "activity_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("analysis_sessions.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(60), index=True)
    message: Mapped[str] = mapped_column(String(500))
    payload: Mapped[dict] = mapped_column("metadata", JSON, default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped[AnalysisSession] = relationship(back_populates="activity_events")


settings = get_settings()
engine_kwargs = {}
if settings.database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.database_url, future=True, pool_pre_ping=True, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    migrate_analysis_sessions()
    with SessionLocal() as db:
        ensure_demo_user(db)


def migrate_analysis_sessions() -> None:
    """Small additive migration layer for local demo/product iteration."""
    inspector = inspect(engine)
    if "analysis_sessions" not in inspector.get_table_names():
        return

    existing = {column["name"] for column in inspector.get_columns("analysis_sessions")}
    dialect = engine.dialect.name
    statements: list[str] = []

    if "pipeline_stage" not in existing:
        statements.append(
            "ALTER TABLE analysis_sessions ADD COLUMN pipeline_stage VARCHAR(40) DEFAULT 'new' NOT NULL"
        )
    if "reviewer_notes" not in existing:
        statements.append(
            "ALTER TABLE analysis_sessions ADD COLUMN reviewer_notes TEXT DEFAULT '' NOT NULL"
        )
    if "decision_memo" not in existing:
        if dialect == "postgresql":
            statements.append(
                "ALTER TABLE analysis_sessions ADD COLUMN decision_memo JSONB DEFAULT '{}'::jsonb NOT NULL"
            )
        else:
            statements.append(
                "ALTER TABLE analysis_sessions ADD COLUMN decision_memo JSON DEFAULT '{}' NOT NULL"
            )

    if not statements:
        return

    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_demo_user(db: Session) -> User:
    settings = get_settings()
    user = db.query(User).filter(User.email == settings.demo_user_email).first()
    if user:
        return user

    user = User(email=settings.demo_user_email, name=settings.demo_user_name)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
