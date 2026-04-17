from fastapi import Header, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status
from starlette.requests import Request
from fastapi.security import OAuth2PasswordBearer
from app.core.db_config import get_db
from app.core.redis_config import redis_client
from app.utils.jwt_util import verify_jwt_token

# 基于OAuth2PasswordBearer和jwt校验token
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/user/login", # 指定获取token的接口
    scheme_name="Bearer" # 指定请求头中的认证方式，即请求头格式为Authorization:Bearer + 空格 + token
)


# ========== 关键修改：自定义token提取依赖 ==========
async def get_token_from_header(request: Request):
    """
    自定义提取token：兼容两种格式
    1. Authorization: Bearer <token>（标准）
    2. Authorization: <token>（前端当前格式）
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请求头缺少Authorization",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 拆分token：兼容有无Bearer前缀
    parts = auth_header.split()
    if len(parts) == 1:
        # 无Bearer前缀，直接取token
        token = parts[0]
    elif len(parts) == 2 and parts[0].lower() == "bearer":
        # 有Bearer前缀，取第二部分
        token = parts[1]
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization格式错误（应为Bearer <token> 或直接传token）",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token



async def verify_token(
        token: str = Depends(oauth2_scheme),
        # token: str = Depends(get_token_from_header),
        db: AsyncSession = Depends(get_db)):
    """
    校验token是否有效
    :param token
    :param db: 数据库连接对象
    :return: 当前用户id信息
    """

    # 第一步：检查 Token是否存在
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的令牌")

    # 第二步：检查 Token 是否在 Redis 黑名单中
    if redis_client.exists(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 已失效（已登出）",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 第二步：验证 Token 签名和有效期
    json_obj = verify_jwt_token(token)

    return json_obj["user_id"]






