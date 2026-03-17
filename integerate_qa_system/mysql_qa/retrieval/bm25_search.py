import sys, os
from rank_bm25 import BM25Okapi
import jieba
from rich import print
import numpy as np

module_path = os.path.dirname(os.path.dirname(__file__))
project_root = os.path.dirname(module_path)
sys.path.insert(0, module_path)
sys.path.insert(0, project_root)

from utils.preprocess import process_text
from db.mysql_client import MysqlClient
from cache.redis_client import RedisClient
from base import logger


class BM25Search:
    def __init__(self, mysql_client: MysqlClient, redis_client: RedisClient):
        # 1. 初始化日志
        self.logger = logger
        # 2.初始化Redis客户端
        self.redis_client = redis_client
        # 3.初始化Mysql客户端
        self.mysql_client = mysql_client
        # 4.初始化BM25模型
        self.bm25 = None
        # 5.初始化问题列表
        self.questions = None
        # 6.初始化原始问题
        self.original_questions = None
        # 7.加载数据
        self._load_data()

    def _load_data(self):
        # 加载数据
        original_key = 'qa_original_questions'
        tokenized_key = 'qa_tokenized_questions'
        # 1.从redis中获取原始的问题
        self.original_questions = self.redis_client.get_data(original_key)

        # 2.从redis中获取分词后的问题
        tokenized_questions = self.redis_client.get_data(tokenized_key)

        # 3.如果redis中没有获取到questions -> 到Mysql中加载数据
        if not self.original_questions or not tokenized_questions:
            # 1. 从mysql中加载数据
            self.original_questions = [q[0] for q in self.mysql_client.fetch_questions()]
            if not self.original_questions:
                self.logger.warning('Mysql中未加载到questions')
            # 2.对questions进行分词处理
            tokenized_questions = [process_text(q) for q in self.original_questions]
            # 3.将questions存储到redis中
            self.redis_client.set_data(original_key, self.original_questions)
            self.redis_client.set_data(tokenized_key, tokenized_questions)

        # 4.加载问题
        self.questions = tokenized_questions

        # 5.加载BM25模型
        self.bm25 = BM25Okapi(self.questions)
        self.logger.info('BM25模型 初始化完成')

    def _softmax(self, scores):
        # 1. 归一化处理, 同时减去最大值, 避免e^n导致 无穷大报错
        exp_scores = np.exp(scores - np.max(scores))
        # 2. 计算softmax 处理结果
        return exp_scores / exp_scores.sum()

    def search(self, query, threshold=0.85):
        # 1. 如果query是空值或者非字符串类型 -> 无效查询
        if not query or not isinstance(query, str):
            self.logger.error('无效查询')
            return None, False

        # 2.查询redis缓存
        cache_answer = self.redis_client.get_answer(query)
        if cache_answer:
            return cache_answer, False
        # 3.查询mysql数据库
        try:
            # 1.对query进行分词处理
            tokenized_query = process_text(query)
            # 2.使用BM25计算得分
            scores = self.bm25.get_scores(tokenized_query)
            # 3.进行softmax处理
            softmax_scores = self._softmax(scores)
            # 4.获取最大分数所以
            beg_index = softmax_scores.argmax()
            # 5.获得最大分数
            beg_score = softmax_scores[beg_index]
            # 6.判断分数是否超过阈值
            if beg_score >= threshold:
                # 1.获取query
                original_question = self.original_questions[beg_index]
                # 2.根据query查询Mysql -> answer
                answer = self.mysql_client.fetch_answer_by_question(original_question)
                if answer:
                    # 3.将answer缓存到redis中
                    self.redis_client.set_data(f'answer:{query}', answer)
                    self.logger.info(f'Mysql快速搜索成功, softmax_score: {beg_score:.3f}')
                    # 4.返回答案
                    return answer, False
            # 7.未找到可靠答案
            self.logger.info(f"未找到可靠答案，最高 Softmax 相似度: {beg_score:.3f}")
            return None, True
        except Exception as e:
            self.logger.error('数据检索失败')
            return None, True


if __name__ == '__main__':
    mysql_client = MysqlClient()
    redis_client = RedisClient()
    bm_search = BM25Search(mysql_client, redis_client)
    print(bm_search.search('用上下文管理器实现函数运行时间的计算?'))
