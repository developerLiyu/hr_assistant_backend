"""
jwt生成令牌工具类
"""
import os
import jwt
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from starlette import status

# 密钥（自己定义，必须保密）
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
# 加密算法
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
# 过期时间（小时）
TOKEN_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRES", 24))

# 1. 生成JWT令牌（用户登录成功后调用）
def create_jwt_token(user_id: int):
    # print(f"DEBUG: SECRET_KEY = '{SECRET_KEY}'")  # 临时调试

    # 设置令牌有效期
    expires_at = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)

    # 载荷：存用户信息+有效期
    payload = {
        "user_id": user_id,
        "exp": int(expires_at.timestamp())
    }
    # 生成令牌
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token




# 2. 验证JWT令牌（前端请求时校验）
def verify_jwt_token(token: str):
    """
    验证 Token：检查是否过期 + 是否在黑名单
    :param token:
    :return: user_id
    """
    # 验证 Token 签名和有效期
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的 Token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return {"status": "success", "user_id": payload["user_id"], "exp": payload["exp"]}
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 已过期或无效",
            headers={"WWW-Authenticate": "Bearer"},
        )

