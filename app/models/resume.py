from sqlalchemy import BigInteger, String, Integer, JSON, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.mysql import MEDIUMTEXT, TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime

from app.models.model_base import Base


class Resume(Base):
    __tablename__ = "resume"
    __table_args__ = (
        Index("idx_position", "position_id"),
        Index("idx_status", "status"),
        Index("idx_education", "education"),
        Index("idx_work_years", "work_years"),
        Index("idx_parse_status", "parse_status"),
        Index("idx_deleted", "is_deleted"),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci", "comment": "简历表"}
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    candidate_name: Mapped[str] = mapped_column(String(50), nullable=False, comment="候选人姓名")
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="手机号")
    email: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="邮箱")
    education: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="学历")
    school: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="毕业院校")
    major: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="专业")
    work_years: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="工作年限")
    current_company: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="当前公司")
    current_position: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="当前职位")
    skills: Mapped[list | None] = mapped_column(JSON, nullable=True, comment="技能标签")
    work_experience: Mapped[list | None] = mapped_column(JSON, nullable=True, comment="工作经历")
    project_experience: Mapped[list | None] = mapped_column(JSON, nullable=True, comment="项目经验")
    education_experience: Mapped[list | None] = mapped_column(JSON, nullable=True, comment="教育经历")
    resume_summary: Mapped[str | None] = mapped_column(Text, nullable=True, comment="AI简历摘要")
    original_content: Mapped[str | None] = mapped_column(MEDIUMTEXT, nullable=True, comment="简历原始文本")
    file_path: Mapped[str] = mapped_column(String(500), nullable=False, comment="文件存储路径")
    file_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="原始文件名")
    file_type: Mapped[str] = mapped_column(String(10), nullable=False, comment="文件类型")
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="文件大小")
    milvus_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    position_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("job_position.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[int] = mapped_column(TINYINT, default=1, nullable=False, comment="状态")
    parse_status: Mapped[int] = mapped_column(TINYINT, default=0, nullable=False, comment="解析状态")
    is_deleted: Mapped[int] = mapped_column(TINYINT, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)