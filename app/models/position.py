from sqlalchemy import Column, BigInteger, String, Text, Integer, SmallInteger, DateTime
from sqlalchemy.sql import func
from app.models.model_base import Base

class JobPosition(Base):
    """岗位表"""
    __tablename__ = "job_position"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    position_name = Column(String(100), nullable=False, comment="岗位名称")
    department = Column(String(100), nullable=False, comment="所属部门")
    job_description = Column(Text, nullable=False, comment="岗位职责描述")
    requirements = Column(Text, nullable=False, comment="任职要求")
    salary_range = Column(String(50), nullable=True, comment="薪资范围")
    work_location = Column(String(100), nullable=True, comment="工作地点")
    headcount = Column(Integer, default=1, comment="招聘人数")
    status = Column(SmallInteger, nullable=False, default=1, comment="状态：1-开放 2-暂停 3-关闭")
    is_deleted = Column(SmallInteger, nullable=False, default=0, comment="软删除：0-正常 1-已删除")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")