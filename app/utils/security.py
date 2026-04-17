from passlib.context import CryptContext

# 创建密码上下文对象
pwd_context = CryptContext(
    schemes=["bcrypt"], # 密码加密算法
    deprecated="auto" # 自动兼容算法过期或者升级
)

# 密码加密函数
def get_hash_password(password: str) -> str:
    return pwd_context.hash(password)

# 密码验证函数
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证密码
    :param plain_password: 明文密码
    :param hashed_password: 密文密码
    """
    return pwd_context.verify(plain_password, hashed_password)

