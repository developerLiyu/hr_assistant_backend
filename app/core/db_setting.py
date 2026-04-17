from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    # 数据库配置
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DATABASE: str = "hr_assistant"

    @property # 属性装饰器
    def DATABASE_URL(self) -> str:
        return f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}?charset=utf8mb4"

    # # 从.env文件中读取配置（要求变量名和.env文件的配置key相同）
    # # Pydantic v1 的配置方式
    # class Config:
    #     env_file = ".env"

    # Pydantic v2 的配置方式  extra='ignore'：忽略多余的参数
    model_config = SettingsConfigDict(env_file=".env", extra='ignore')

@lru_cache() # 实现单例模式，保证只有一个实例，并存到缓存中。提高性能，避免重复创建实例（即重复读取配置文件）
def get_settings():
    return Settings()

settings = get_settings()