from sqlalchemy import BigInteger, Text, DateTime, ForeignKey, Index, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime

from app.models.model_base import Base


class InterviewSummary(Base):
    __tablename__ = "interview_summary"
    __table_args__ = (
        UniqueConstraint("resume_id", name="uk_recording"),
        Index("idx_resume", "resume_id"),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci", "comment": "面试摘要表"}
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    recording_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("interview_recording.id", ondelete="CASCADE"), nullable=False, comment="关联录音ID")
    resume_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("resume.id", ondelete="CASCADE"), nullable=False, comment="关联简历ID")
    summary_overview: Mapped[str] = mapped_column(Text(collation="utf8mb4_unicode_ci"), nullable=False, comment="面试概要")
    key_qa: Mapped[dict | list | None] = mapped_column(JSON, nullable=True, comment="核心问答")
    technical_skills: Mapped[dict | list | None] = mapped_column(JSON, nullable=True, comment="技术能力标签")
    soft_skills: Mapped[dict | list | None] = mapped_column(JSON, nullable=True, comment="软技能标签")
    highlights: Mapped[str | None] = mapped_column(Text(collation="utf8mb4_unicode_ci"), nullable=True, comment="亮点")
    concerns: Mapped[str | None] = mapped_column(Text(collation="utf8mb4_unicode_ci"), nullable=True, comment="疑虑点")
    candidate_questions: Mapped[str | None] = mapped_column(Text(collation="utf8mb4_unicode_ci"), nullable=True, comment="候选人问题")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间")
