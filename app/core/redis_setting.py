from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    # redis配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""

    # # 从.env文件中读取配置（要求变量名和.env文件的配置key相同）
    # # Pydantic v1 的配置方式
    # class Config:
    #     env_file = ".env"

    # Pydantic v2 的配置方式
    model_config = SettingsConfigDict(env_file=".env", extra='ignore')


@lru_cache() # 实现单例模式，保证只有一个实例，并存到缓存中。提高性能，避免重复创建实例（即重复读取配置文件）
def get_settings():
    return Settings()

settings = get_settings()