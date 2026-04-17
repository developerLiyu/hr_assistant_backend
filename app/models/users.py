from datetime import datetime
from sqlalchemy import Column, BigInteger, String, DateTime, text
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import declarative_base

from app.models.model_base import Base

class SysUser(Base):
    """
    系统用户表 ORM 模型
    对应数据库表：sys_user
    """
    # 数据库表名
    __tablename__ = "sys_user"

    # 主键ID（bigint 自增）
    id = Column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="主键ID"
    )
    # 用户名（唯一非空）
    username = Column(
        String(50),
        nullable=False,
        unique=True,
        comment="用户名"
    )
    # 密码（加密，非空）
    password = Column(
        String(100),
        nullable=False,
        comment="密码(加密)"
    )
    # 真实姓名（可空）
    real_name = Column(
        String(50),
        nullable=True,
        comment="真实姓名"
    )
    # 邮箱（可空）
    email = Column(
        String(100),
        nullable=True,
        comment="邮箱"
    )
    # 手机号（可空）
    phone = Column(
        String(20),
        nullable=True,
        comment="手机号"
    )
    # 头像URL（可空）
    avatar = Column(
        String(500),
        nullable=True,
        comment="头像URL"
    )
    # 状态（1-正常 0-禁用，默认1）
    status = Column(
        TINYINT,
        nullable=False,
        default=1,
        server_default=text("1"),
        comment="状态：1-正常 0-禁用"
    )
    # 最后登录时间（可空）
    last_login_time = Column(
        DateTime,
        nullable=True,
        comment="最后登录时间"
    )
    # 创建时间（数据库自动生成）
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        comment="创建时间"
    )
    # 更新时间（自动更新）
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
        comment="更新时间"
    )

    # 表级配置：引擎、字符集、排序规则、表注释
    __table_args__ = (
        {
            "mysql_engine": "InnoDB",
            "mysql_charset": "utf8mb4",
            "mysql_collate": "utf8mb4_unicode_ci",
            "comment": "用户表",
            # "autoincrement": 2  # 对齐建表语句 AUTO_INCREMENT=2  设置这个访问会报错，应该在具体的列Column中设置
        }
    )