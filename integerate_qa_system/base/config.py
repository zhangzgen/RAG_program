# _*_coding:utf-8-*-
import configparser
import os

current_file_abspath = os.path.abspath(__file__)
config_dir_path = os.path.dirname(os.path.dirname(current_file_abspath))
config_file_abspath = os.path.join(config_dir_path, 'config.ini')

HOT_RELOADABLE_SECTIONS = {
    'llm': ['model', 'api_key', 'base_url', 'enable_thinking', 'thinking_budget_tokens'],
    'assessment': ['llm_model', 'embedding_model', 'api_key', 'base_url'],
    'retrieval': ['parent_chunk_size', 'child_chunk_size', 'chunk_overlap', 'retrieval_k', 'candidate_m'],
    'app': ['valid_sources', 'customer_service_phone'],
    'email': ['qq_email', 'qq_auth_code', 'smtp_server', 'smtp_port'],
    'jwt': ['secret_key', 'algorithm', 'expire_days']
}

NOT_RELOADABLE_SECTIONS = {
    'mysql': ['host', 'user', 'password', 'database'],
    'redis': ['host', 'port', 'password', 'db'],
    'milvus': ['host', 'port', 'database_name', 'collection_name'],
    'logger': ['log_file']
}

THINKING_MODELS = [
    'deepseek-reasoner',
    'deepseek-r1',
    'qwen3',
    'qwen3-235b-a22b',
    'qwen3-32b',
]


class Config:
    _instance = None
    _config_cache = None

    def __new__(cls, config_file=config_file_abspath):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config_file=config_file_abspath):
        force_reload = hasattr(self, '_force_reload')
        if Config._config_cache is not None and not force_reload:
            self.__dict__.update(Config._config_cache)
            return

        self.config = configparser.ConfigParser()
        self.config.read(config_file, encoding='utf-8')
        self._load_all_config()
        if force_reload and hasattr(self, '_force_reload'):
            delattr(self, '_force_reload')
        Config._config_cache = self.__dict__.copy()

    def _load_all_config(self):
        self.MYSQL_HOST = self.config.get('mysql', 'host', fallback='localhost')
        self.MYSQL_USER = self.config.get('mysql', 'user', fallback='root')
        self.MYSQL_PASSWORD = self.config.get('mysql', 'password', fallback='123456')
        self.MYSQL_DATABASE = self.config.get('mysql', 'database', fallback='subjects_kg')

        self.REDIS_HOST = self.config.get('redis', 'host', fallback='localhost')
        self.REDIS_PORT = self.config.getint('redis', 'port', fallback=6379)
        self.REDIS_PASSWORD = self.config.get('redis', 'password', fallback='1234')
        self.REDIS_DB = self.config.getint('redis', 'db', fallback=0)

        self.MILVUS_HOST = self.config.get('milvus', 'host', fallback='localhost')
        self.MILVUS_PORT = self.config.get('milvus', 'port', fallback='19530')
        self.MILVUS_DATABASE_NAME = self.config.get('milvus', 'database_name', fallback='itcast')
        self.MILVUS_COLLECTION_NAME = self.config.get('milvus', 'collection_name', fallback='edurag_final')

        self.LLM_MODEL = self.config.get('llm', 'model', fallback='qwen-plus')
        self.LLM_API_KEY = self.config.get('llm', 'api_key', fallback='') or self.config.get('llm', 'dashscope_api_key', fallback='')
        self.LLM_BASE_URL = self.config.get('llm', 'base_url', fallback='') or self.config.get('llm', 'dashscope_base_url', fallback='https://dashscope.aliyuncs.com/compatible-mode/v1')

        if self.LLM_BASE_URL and not self.LLM_BASE_URL.endswith('/v1'):
            if 'deepseek' in self.LLM_BASE_URL.lower():
                self.LLM_BASE_URL = self.LLM_BASE_URL.rstrip('/') + '/v1'

        self.ENABLE_THINKING = self.config.getboolean('llm', 'enable_thinking', fallback=False)
        self.THINKING_BUDGET_TOKENS = self.config.getint('llm', 'thinking_budget_tokens', fallback=10000)

        self.DASHSCOPE_API_KEY = self.LLM_API_KEY
        self.DASHSCOPE_BASE_URL = self.LLM_BASE_URL

        # support both 'model' and 'llm_model' keys in [assessment]
        _asmt_model = self.config.get('assessment', 'model', fallback=None) or \
                      self.config.get('assessment', 'llm_model', fallback=self.LLM_MODEL)
        self.ASSESSMENT_LLM_MODEL = _asmt_model
        self.ASSESSMENT_API_KEY = self.config.get('assessment', 'api_key', fallback='') or ''
        self.ASSESSMENT_BASE_URL = self.config.get('assessment', 'base_url', fallback='http://localhost:11434') or 'http://localhost:11434'
        self.ASSESSMENT_EMBEDDING_BASE_URL = self.config.get('assessment', 'embedding_base_url', fallback=None) or self.ASSESSMENT_BASE_URL
        # auto-detect provider from base_url
        self.ASSESSMENT_EMBEDDING_PROVIDER = 'ollama' if '11434' in self.ASSESSMENT_BASE_URL or '11434' in self.ASSESSMENT_EMBEDDING_BASE_URL else 'openai'
        # auto-pick default embedding model based on provider/base_url
        _default_emb = 'mxbai-embed-large' if self.ASSESSMENT_EMBEDDING_PROVIDER == 'ollama' \
            else ('text-embedding-v3' if 'dashscope' in self.ASSESSMENT_BASE_URL else 'text-embedding-3-small')
        self.ASSESSMENT_EMBEDDING_MODEL = self.config.get('assessment', 'embedding_model', fallback=_default_emb) or _default_emb

        self.PARENT_CHUNK_SIZE = self.config.getint('retrieval', 'parent_chunk_size', fallback=1200)
        self.CHILD_CHUNK_SIZE = self.config.getint('retrieval', 'child_chunk_size', fallback=300)
        self.CHUNK_OVERLAP = self.config.getint('retrieval', 'chunk_overlap', fallback=50)
        self.RETRIEVAL_K = self.config.getint('retrieval', 'retrieval_k', fallback=5)
        self.CANDIDATE_M = self.config.getint('retrieval', 'candidate_m', fallback=2)

        self.VALID_SOURCES = eval(
            self.config.get('app', 'valid_sources', fallback='["ai", "java", "test", "ops", "bigdata"]'))
        self.CUSTOMER_SERVICE_PHONE = self.config.get('app', 'customer_service_phone', fallback='12345678')
        self.LOG_FILE = self.config.get('logger', 'log_file', fallback='logs/app.log')

        self.QQ_EMAIL = self.config.get('email', 'qq_email', fallback='your_qq_email@qq.com')
        self.QQ_AUTH_CODE = self.config.get('email', 'qq_auth_code', fallback='your_qq_auth_code')
        self.SMTP_SERVER = self.config.get('email', 'smtp_server', fallback='smtp.qq.com')
        self.SMTP_PORT = self.config.getint('email', 'smtp_port', fallback=465)

        self.JWT_SECRET_KEY = self.config.get('jwt', 'secret_key', fallback='your_jwt_secret_key_here_change_in_production')
        self.JWT_ALGORITHM = self.config.get('jwt', 'algorithm', fallback='HS256')
        self.JWT_EXPIRE_DAYS = self.config.getint('jwt', 'expire_days', fallback=30)

    def is_thinking_model(self):
        """检查当前模型是否为思考模型"""
        model_lower = self.LLM_MODEL.lower()
        return any(tm in model_lower for tm in THINKING_MODELS) or self.ENABLE_THINKING

    @classmethod
    def hot_reload(cls, config_file=config_file_abspath):
        """
        热加载配置文件

        Returns:
            dict: 包含热加载结果的字典
        """
        cls._config_cache = None
        instance = cls.__new__(cls)
        instance._force_reload = True
        instance.__init__(config_file)
        if hasattr(instance, '_force_reload'):
            delattr(instance, '_force_reload')

        reloaded = []
        not_reloaded = []

        for section, keys in HOT_RELOADABLE_SECTIONS.items():
            for key in keys:
                reloaded.append(f"{section}.{key}")

        for section, keys in NOT_RELOADABLE_SECTIONS.items():
            for key in keys:
                not_reloaded.append(f"{section}.{key}")

        return {
            'success': True,
            'reloaded': reloaded,
            'not_reloaded': not_reloaded,
            'reloaded_count': len(reloaded),
            'not_reloaded_count': len(not_reloaded)
        }


if __name__ == '__main__':
    conf = Config()
    print(conf.CHILD_CHUNK_SIZE)
