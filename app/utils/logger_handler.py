import logging
import os
from datetime import datetime

from app.utils.path_tool import get_abs_path

# 日志保存的根目录
LOG_ROOT = get_abs_path("logs")

# 确保日志的目录存在
os.makedirs(LOG_ROOT, exist_ok=True)

# 日志的格式配置  error info debug
DEFAULT_LOG_FORMAT = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
)

def get_logger(
        name: str = "assistant",
        console_level: int = logging.INFO,
        file_level: int = logging.DEBUG,
        log_file = None
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # 检查是否已经有相同的 handler 避免重复添加
    has_file_handler = any(isinstance(handler, logging.FileHandler) for handler in logger.handlers)

    # 控制台Handler
    has_console_handler = any(isinstance(handler, logging.StreamHandler) for handler in logger.handlers)

    if not has_console_handler:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(console_level)
        console_handler.setFormatter(DEFAULT_LOG_FORMAT)
        logger.addHandler(console_handler)

    if not has_file_handler:
        # 文件Handler
        if not log_file:
            log_file = os.path.join(LOG_ROOT, f"{name}_{datetime.now().strftime('%Y-%m-%d')}.log")
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(file_level)
        file_handler.setFormatter(DEFAULT_LOG_FORMAT)
        logger.addHandler(file_handler)

    return logger

# 快捷获取日志器
logger = get_logger()

if __name__ == '__main__':
    logger.info("信息日志")
    logger.error("错误日志")
    logger.warning("警告日志")
    logger.debug("调试日志")

