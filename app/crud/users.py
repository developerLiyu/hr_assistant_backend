"""
用户数据库操作
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.users import SysUser
from app.utils import security


async def get_user_by_username(username: str, db: AsyncSession, ):
    """
    根据用户名获取用户信息
    :param db: 数据库连接对象
    :param username: 用户名
    :return: 用户信息
    """
    query = select(SysUser).where(SysUser.username == username)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_user(username: str, password: str, db: AsyncSession):
    """
    验证用户是否存在
    :param db: 数据库连接对象
    :param username: 用户名
    :param password: 密码
    :return: 用户信息
    """
    user = await get_user_by_username(username, db)

    if not user:
        # 用户不存在
        return None
    if not security.verify_password(password, user.password):
        # 密码错误
        return None

    # 用户存在
    return user



async def get_user_by_id( user_id: int, db: AsyncSession):
    """
    根据用户id获取用户
    :param db:
    :param user_id:
    :return:
    """
    query = select(SysUser).where(SysUser.id == user_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()





