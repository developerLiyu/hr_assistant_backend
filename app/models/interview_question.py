from sqlalchemy import BigInteger, String, Text, JSON, DateTime, ForeignKey, Index, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime

from app.models.model_base import Base


class InterviewQuestion(Base):
    __tablename__ = "interview_question"
    __table_args__ = (
        Index("idx_position", "position_id"),
        Index("idx_resume", "resume_id"),
        Index("idx_type", "question_type"),
        Index("idx_difficulty", "difficulty"),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci", "comment": "面试题表"}
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    position_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("job_position.id", ondelete="SET NULL"), nullable=True, comment="关联岗位ID")
    resume_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("resume.id", ondelete="SET NULL"), nullable=True, comment="关联简历ID")
    question_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="题目类型：technical/behavioral/situational/open")
    difficulty: Mapped[str] = mapped_column(String(10), nullable=False, comment="难度：junior/middle/senior")
    question_content: Mapped[str] = mapped_column(Text, nullable=False, comment="题目内容")
    reference_answer: Mapped[str | None] = mapped_column(Text, nullable=True, comment="参考答案")
    scoring_points: Mapped[list | None] = mapped_column(JSON, nullable=True, comment="评分要点")
    source: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="题目来源")
    is_saved: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False, comment="是否保存到题库")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False, comment="创建时间")
