import os
import uuid
from app.utils.logger_handler import logger
from dotenv import load_dotenv

load_dotenv()

OSS_ACCESS_KEY_ID = os.getenv("OSS_ACCESS_KEY_ID")
OSS_ACCESS_KEY_SECRET = os.getenv("OSS_ACCESS_KEY_SECRET")
OSS_BUCKET_NAME = os.getenv("OSS_BUCKET_NAME")
OSS_ENDPOINT = os.getenv("OSS_ENDPOINT", "oss-cn-beijing.aliyuncs.com")
OSS_AUDIO_DIR = os.getenv("OSS_AUDIO_DIR", "hr-audio")


def upload_audio_to_oss(local_file_path: str, file_type: str = "wav") -> str:
    """
    将音频文件上传到阿里云 OSS，返回公网可访问的 URL
    :param local_file_path: 本地音频文件路径
    :param file_type: 音频格式（wav/mp3/m4a/aac）
    :return: OSS 公网 URL
    """
    try:
        import oss2

        auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)
        bucket = oss2.Bucket(auth, f"https://{OSS_ENDPOINT}", OSS_BUCKET_NAME)

        # 生成 OSS 上的文件名
        oss_filename = f"{OSS_AUDIO_DIR}/{uuid.uuid4().hex}.{file_type}"

        # 上传文件
        with open(local_file_path, "rb") as f:
            bucket.put_object(oss_filename, f)

        # 返回公网 URL
        oss_url = f"https://{OSS_BUCKET_NAME}.{OSS_ENDPOINT}/{oss_filename}"
        logger.info(f"音频文件上传 OSS 成功：{oss_url}")
        return oss_url

    except ImportError:
        logger.error("未安装 oss2 库，请执行: pip install oss2")
        raise
    except Exception as e:
        logger.error(f"上传音频到 OSS 失败: {str(e)}", exc_info=True)
        raise


def delete_oss_file(oss_url: str) -> bool:
    """
    删除 OSS 上的文件
    :param oss_url: OSS 公网 URL
    :return: 是否删除成功
    """
    try:
        import oss2
        from urllib.parse import urlparse

        auth = oss2.Auth(OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET)

        # 从 URL 中提取 object name
        parsed = urlparse(oss_url)
        oss_filename = parsed.path.lstrip("/")

        bucket = oss2.Bucket(auth, f"https://{OSS_ENDPOINT}", OSS_BUCKET_NAME)
        bucket.delete_object(oss_filename)

        logger.info(f"OSS 文件删除成功：{oss_filename}")
        return True

    except Exception as e:
        logger.error(f"删除 OSS 文件失败: {str(e)}", exc_info=True)
        return False
