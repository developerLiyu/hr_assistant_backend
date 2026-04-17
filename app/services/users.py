import os

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import users
from app.schemas.users import UserRequest
from app.utils.jwt_util import create_jwt_token


async def get_user(user_data: UserRequest, db: AsyncSession):
    """
    获取用户信息
    :param db:
    :param username:
    :param password:
    :return:
    """
    user = await users.get_user(user_data.username, user_data.password, db)
    return user






