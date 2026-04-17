import json
from typing import Any
import redis.asyncio as redis
from app.core.redis_setting import settings
from app.utils.logger_handler import logger

redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD,
    decode_responses=True # 是否将字节数据解码为字符串
)

# 读取缓存信息（字符串）
async def get_cache(key: str):
    try:
        return await redis_client.get(key)

    except Exception as e:
        logger.error(f"读取缓存失败（字符串内容）: {e}", exc_info=True)
    return None


# 读取缓存信息（字典或者列表）
async def get_json_cache(key: str):
    try:
        # 读取数据，并转换为对象
        data = await redis_client.get(key)

        if not data:
            return None
        else:
            return json.loads(data)  # 去掉引号""

    except Exception as e:
        logger.error(f"读取缓存失败（字典或者列表）: {e}", exc_info=True)
        return None


# 设置缓存信息
async def set_cache(key: str, value: Any, expire: int = 3600):
    try:
        if isinstance(value, (dict, list)):
            # 将数据转换成字符串，确保非ascii字符（即不转换，可以有中文）
            # 即加上引号""
            value = json.dumps(value, ensure_ascii=False)

        # 设置缓存信息
        await redis_client.setex(key, expire, value)
        return True

    except Exception as e:
        logger.error(f"设置缓存失败: {e}", exc_info=True)
        return False


