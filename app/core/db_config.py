from sys import exc_info

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession, create_async_engine
from app.core.db_setting import settings
from app.utils.logger_handler import logger

# 创建异步引擎
async_engine = create_async_engine(
    settings.DATABASE_URL, # 数据库连接字符串
    echo=True,  # 是否打印sql
    pool_size=10,  # 连接池大小(持久连接数)
    max_overflow=20,  # 连接池溢出时最大连接数
    pool_pre_ping=True # 确保每次使用的连接都是活的
)

# 创建异步会话
async_session = async_sessionmaker(
    bind=async_engine, # 数据库异步连接引擎
    class_=AsyncSession, # 会话类型
    expire_on_commit=False # 是否在提交时关闭会话
)

# 创建依赖函数，用于获取数据库会话
async def get_db():
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.exception("操作出现异常，执行回滚")
            raise
        finally:
            await session.close()
