import logging
from .config import Config
import os

# 获取日志文件目录
current_file_abspath = os.path.abspath(__file__)
system_dir_path = os.path.dirname(os.path.dirname(current_file_abspath))
log_file_abspath = os.path.join(system_dir_path, Config().LOG_FILE)


# print(log_file_abspath)


def setup_logging(log_file=log_file_abspath):
    # 1. 创建日志目录
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # 2.获取日志器
    logger = logging.getLogger('Edu_RAG')

    # 3.设置日志级别
    logger.setLevel(logging.INFO)

    # 4.添加日志处理器
    if not logger.handlers:
        # 1. 创建日志文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        # 设置日志级别
        file_handler.setLevel(logging.INFO)

        # 2.创建控制台处理器
        stream_handler = logging.StreamHandler()
        # 设置日志级别
        stream_handler.setLevel(logging.INFO)

        # 3.设置日志格式
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        stream_handler.setFormatter(formatter)

        # 4.添加日志处理器
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)

    # 5.返回日志器对象
    return logger


logger = setup_logging()

