# 导入Redis客户端
from cache.redis_client import RedisClient
# 导入Mysql客户端
from db.mysql_client import MysqlClient
# 导入BM25检索类
from retrieval.bm25_search import BM25Search
# 导入配置文件对象
from base import logger
# 导入时间对象
import time


class MysqlQASystem:
    def __init__(self):
        # 初始化日志器
        self.logger = logger
        # 初始化Redis客户端
        self.redis_client = RedisClient()
        # 初始化Mysql客户端
        self.mysql_client = MysqlClient()
        # 初始化BM25检索器
        self.bm25_search = BM25Search(self.mysql_client, self.redis_client)

    def query(self, query):
        # 1. 检录检索开始时间
        start_time = time.time()
        # 2.检索答案
        self.logger.info(f'Mysql数据检索: {query}')
        answer, _ = self.bm25_search.search(query)
        if answer:
            self.logger.info(f'Mysql检索到数据: {answer}')
        else:
            self.logger.info('Mysql数据库未检索到数据, 需要调用RAG系统')
            # 设置默认答案
            answer = 'Mysql数据库未检索到答案'
        # 3.计算检索时间
        process_time = time.time() - start_time
        self.logger.info(f'Mysql检索耗时: {process_time:.2f}s')
        # 4.返回答案
        return answer


def main():
    # 初始化 MySQL 系统
    mysql_system = MysqlQASystem()
    try:
        # 打印欢迎信息
        print("\n欢迎使用 MySQL 问答系统！")
        print("输入查询进行问答，输入 'exit' 退出。")
        while True:
            # 获取用户输入
            query = input("\n输入查询: ").strip()
            if query.lower() == "exit":
                # 记录退出日志
                logger.info("退出 MySQL 系统")
                # 打印退出信息
                print("再见！")
                break
            # 执行查询
            answer = mysql_system.query(query)
            # 打印答案
            print(f"\n答案: {answer}")
    except Exception as e:
        # 记录系统错误
        logger.error(f"系统错误: {e}")
        # 打印错误信息
        print(f"发生错误: {e}")
    finally:
        # 关闭 MySQL 连接
        mysql_system.mysql_client.close()

if __name__ == "__main__":
    # 运行主程序
    main()
