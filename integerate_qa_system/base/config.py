# _*_coding:utf-8-*-
import configparser
import os

# 获取读取文件所在的绝对路径
current_file_abspath = os.path.abspath(__file__)

# 获取配置文件所在 文件夹绝对路径
# os.path.dirname(path) -> 获取path的上一级目录
config_dir_path = os.path.dirname(os.path.dirname(current_file_abspath))

# 拼接得到配置文件的绝对路径
config_file_abspath = os.path.join(config_dir_path, 'config.ini')


class Config:
    # 初始化配置，加载 config.ini 文件
    def __init__(self, config_file=config_file_abspath):
        # 创建配置解析器
        self.config = configparser.ConfigParser()
        # 读取配置文件
        self.config.read(config_file, encoding='utf-8')

        # MySQL 配置
        # MySQL 主机地址
        self.MYSQL_HOST = self.config.get('mysql', 'host', fallback='localhost')
        # MySQL 用户名
        self.MYSQL_USER = self.config.get('mysql', 'user', fallback='root')
        # MySQL 密码
        self.MYSQL_PASSWORD = self.config.get('mysql', 'password', fallback='123456')
        # MySQL 数据库名
        self.MYSQL_DATABASE = self.config.get('mysql', 'database', fallback='subjects_kg')

        # Redis 配置
        # Redis 主机地址
        self.REDIS_HOST = self.config.get('redis', 'host', fallback='localhost')
        # Redis 端口
        self.REDIS_PORT = self.config.getint('redis', 'port', fallback=6379)
        # Redis 密码
        self.REDIS_PASSWORD = self.config.get('redis', 'password', fallback='1234')
        # Redis 数据库编号
        self.REDIS_DB = self.config.getint('redis', 'db', fallback=0)

        # Milvus 配置
        # Milvus 主机地址
        self.MILVUS_HOST = self.config.get('milvus', 'host', fallback='localhost')
        # Milvus 端口
        self.MILVUS_PORT = self.config.get('milvus', 'port', fallback='19530')
        # Milvus 数据库名
        self.MILVUS_DATABASE_NAME = self.config.get('milvus', 'database_name', fallback='itcast')
        # Milvus 集合名
        self.MILVUS_COLLECTION_NAME = self.config.get('milvus', 'collection_name', fallback='edurag_final')

        # LLM 配置
        # LLM 模型名
        self.LLM_MODEL = self.config.get('llm', 'model', fallback='qwen-plus')
        # DashScope API 密钥
        self.DASHSCOPE_API_KEY = self.config.get('llm', 'dashscope_api_key')
        # DashScope API 地址
        self.DASHSCOPE_BASE_URL = self.config.get('llm', 'dashscope_base_url',
                                                  fallback='https://dashscope.aliyuncs.com/compatible-mode/v1')

        # 检索参数
        # 父块大小
        self.PARENT_CHUNK_SIZE = self.config.getint('retrieval', 'parent_chunk_size', fallback=1200)
        # 子块大小
        self.CHILD_CHUNK_SIZE = self.config.getint('retrieval', 'child_chunk_size', fallback=300)
        # 块重叠大小
        self.CHUNK_OVERLAP = self.config.getint('retrieval', 'chunk_overlap', fallback=50)
        # 检索返回数量
        self.RETRIEVAL_K = self.config.getint('retrieval', 'retrieval_k', fallback=5)
        # 最终候选数量
        self.CANDIDATE_M = self.config.getint('retrieval', 'candidate_m', fallback=2)

        # 应用配置
        # 有效来源列表
        self.VALID_SOURCES = eval(
            self.config.get('app', 'valid_sources', fallback='["ai", "java", "test", "ops", "bigdata"]'))
        # 客服电话
        self.CUSTOMER_SERVICE_PHONE = self.config.get('app', 'customer_service_phone', fallback='12345678')
        # 日志文件路径
        self.LOG_FILE = self.config.get('logger', 'log_file', fallback='logs/app.log')

        # 邮箱配置
        # QQ邮箱地址
        self.QQ_EMAIL = self.config.get('email', 'qq_email', fallback='your_qq_email@qq.com')
        # QQ邮箱授权码
        self.QQ_AUTH_CODE = self.config.get('email', 'qq_auth_code', fallback='your_qq_auth_code')
        # SMTP服务器地址
        self.SMTP_SERVER = self.config.get('email', 'smtp_server', fallback='smtp.qq.com')
        # SMTP服务器端口
        self.SMTP_PORT = self.config.getint('email', 'smtp_port', fallback=465)

        # JWT 配置
        # JWT密钥
        self.JWT_SECRET_KEY = self.config.get('jwt', 'secret_key', fallback='your_jwt_secret_key_here_change_in_production')
        # JWT算法
        self.JWT_ALGORITHM = self.config.get('jwt', 'algorithm', fallback='HS256')
        # JWT过期天数
        self.JWT_EXPIRE_DAYS = self.config.getint('jwt', 'expire_days', fallback=30)


if __name__ == '__main__':
    conf = Config()
    print(conf.CHILD_CHUNK_SIZE)