import math
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from jwt import PyJWTError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from app.core import redis_config
from app.core.db_config import get_db
from app.schemas.users import UserRequest, UserAuthResponse, SysUser
from app.services import users
from app.utils import response
from app.utils.auth import oauth2_scheme
from app.utils.jwt_util import create_jwt_token, verify_jwt_token

router = APIRouter(prefix="/api/v1/system", tags=["系统管理"])

# 登录功能
@router.post("/login")
async def login(user_data: UserRequest, db: AsyncSession = Depends(get_db)):
    # 验证用户是否存在（是否有用户、用户名密码是否正确）
    user = await users.get_user(user_data, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或密码错误")

    # 获取token信息
    token = str(create_jwt_token(user.id))

    # 返回信息
    response_data = UserAuthResponse(token=token, user_info=SysUser.model_validate(user))

    return response.response(0, "登录成功", response_data)


# 退出功能
@router.get("/logout")
async def logout(token: str = Depends(oauth2_scheme)):
    """
    登出逻辑：
    1. 获取当前请求的 Token
    2. 存入 Redis 黑名单，过期时间和 Token 一致
    3. 前端同时清除本地存储的 Token
    """

    # 检查 Token是否存在
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的令牌")

    # 解码获取 Token 剩余有效期
    json_obj = verify_jwt_token(token)
    # expire = json_obj["exp"] - datetime.now(timezone.utc).timestamp() # 返回的是浮点数，需要转换成整数
    # math.ceil() 函数返回最接近的整数，向上取整
    expire = math.ceil(json_obj["exp"] - datetime.now(timezone.utc).timestamp())

    if expire > 0:
        # 将 Token 存入 Redis，设置过期时间
        await redis_config.set_cache(token, "blacklisted", expire)

    return response.response(0, "退出成功，Token 已失效")


