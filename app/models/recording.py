from sqlalchemy import BigInteger, String, Integer, Text, DateTime, ForeignKey, Index, Date
from sqlalchemy.dialects.mysql import LONGTEXT, TINYINT
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from datetime import datetime, date

from app.models.model_base import Base


class InterviewRecording(Base):
    __tablename__ = "interview_recording"
    __table_args__ = (
        Index("idx_resume", "resume_id"),
        Index("idx_status", "transcript_status"),
        Index("idx_interview_date", "interview_date"),
        {"mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci", "comment": "面试录音表"}
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    resume_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("resume.id", ondelete="CASCADE"), nullable=False, comment="关联简历ID")
    position_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="关联岗位ID")
    file_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="文件名")
    file_path: Mapped[str] = mapped_column(String(500), nullable=False, comment="存储路径")
    file_type: Mapped[str] = mapped_column(String(10), nullable=False, comment="文件类型：mp3/wav/m4a/aac")
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="文件大小(字节)")
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="时长(秒)")
    transcript: Mapped[str | None] = mapped_column(LONGTEXT, nullable=True, comment="文字稿")
    transcript_status: Mapped[int] = mapped_column(TINYINT, default=0, nullable=False, comment="转写状态：0-未转写 1-转写中 2-已完成 3-失败")
    transcript_error: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="转写错误信息")
    interviewer: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="面试官")
    interview_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="面试日期")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False, comment="更新时间")
