from sqlalchemy import BigInteger, DateTime, Index, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime

from app.models.model_base import Base


class CandidateComparison(Base):
    __tablename__ = "candidate_comparison"
    __table_args__ = (
        Index("idx_position", "position_id"),
        Index("idx_created_at", "created_at"),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci", "comment": "候选人对比表"}
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    position_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="岗位ID")
    resume_ids: Mapped[list | dict] = mapped_column(JSON, nullable=False, comment="简历ID列表")
    comparison_data: Mapped[dict | list | None] = mapped_column(JSON, nullable=True, comment="对比数据快照")
    comparison_summary: Mapped[str | None] = mapped_column(Text(collation="utf8mb4_unicode_ci"), nullable=True, comment="对比总结")
    candidate_analysis: Mapped[dict | list | None] = mapped_column(JSON, nullable=True, comment="候选人分析")
    ranking: Mapped[dict | list | None] = mapped_column(JSON, nullable=True, comment="排名结果")
    recommendation: Mapped[dict | list | None] = mapped_column(JSON, nullable=True, comment="候选人建议")
    hiring_advice: Mapped[str | None] = mapped_column(Text(collation="utf8mb4_unicode_ci"), nullable=True, comment="录用建议")
    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="创建人ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False, comment="创建时间")
