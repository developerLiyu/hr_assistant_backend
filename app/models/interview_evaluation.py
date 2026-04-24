from sqlalchemy import BigInteger, Integer, Text, DateTime, ForeignKey, Index, Numeric, String, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime

from app.models.model_base import Base


class InterviewEvaluation(Base):
    __tablename__ = "interview_evaluation"
    __table_args__ = (
        Index("idx_resume", "resume_id"),
        Index("idx_total_score", "total_score"),
        Index("idx_recommendation", "recommendation"),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci", "comment": "面试评价表"}
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    resume_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("resume.id", ondelete="CASCADE"), nullable=False, comment="关联简历ID")
    recording_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="关联录音ID")
    summary_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="关联摘要ID")
    
    professional_score: Mapped[int] = mapped_column(Integer, nullable=False, comment="专业能力评分")
    professional_comment: Mapped[str | None] = mapped_column(String(200, collation="utf8mb4_unicode_ci"), nullable=True, comment="专业能力评语")
    
    logic_score: Mapped[int] = mapped_column(Integer, nullable=False, comment="逻辑思维评分")
    logic_comment: Mapped[str | None] = mapped_column(String(200, collation="utf8mb4_unicode_ci"), nullable=True, comment="逻辑思维评语")
    
    communication_score: Mapped[int] = mapped_column(Integer, nullable=False, comment="沟通表达评分")
    communication_comment: Mapped[str | None] = mapped_column(String(200, collation="utf8mb4_unicode_ci"), nullable=True, comment="沟通表达评语")
    
    learning_score: Mapped[int] = mapped_column(Integer, nullable=False, comment="学习能力评分")
    learning_comment: Mapped[str | None] = mapped_column(String(200, collation="utf8mb4_unicode_ci"), nullable=True, comment="学习能力评语")
    
    teamwork_score: Mapped[int] = mapped_column(Integer, nullable=False, comment="团队协作评分")
    teamwork_comment: Mapped[str | None] = mapped_column(String(200, collation="utf8mb4_unicode_ci"), nullable=True, comment="团队协作评语")
    
    culture_score: Mapped[int] = mapped_column(Integer, nullable=False, comment="文化匹配评分")
    culture_comment: Mapped[str | None] = mapped_column(String(200, collation="utf8mb4_unicode_ci"), nullable=True, comment="文化匹配评语")
    
    total_score: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, comment="综合得分")
    recommendation: Mapped[str] = mapped_column(String(20, collation="utf8mb4_unicode_ci"), nullable=False, comment="推荐等级：强烈推荐/推荐/一般/不推荐")
    
    ai_comment: Mapped[str | None] = mapped_column(Text(collation="utf8mb4_unicode_ci"), nullable=True, comment="AI综合评语")
    key_strengths: Mapped[dict | list | None] = mapped_column(JSON, nullable=True, comment="核心优势")
    improvement_areas: Mapped[dict | list | None] = mapped_column(JSON, nullable=True, comment="待提升领域")
    hiring_suggestion: Mapped[str | None] = mapped_column(Text(collation="utf8mb4_unicode_ci"), nullable=True, comment="录用建议")
    hr_comment: Mapped[str | None] = mapped_column(Text(collation="utf8mb4_unicode_ci"), nullable=True, comment="HR补充评价")
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间")
