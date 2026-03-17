# 导入 BGE-M3 嵌入函数，用于生成文档和查询的向量表示
import torch
from milvus_model.hybrid import BGEM3EmbeddingFunction

# 导入 Milvus 相关类，用于操作向量数据库
from pymilvus import MilvusClient, DataType, AnnSearchRequest, WeightedRanker
# 导入 Document 类，用于创建文档对象
from langchain.docstore.document import Document
# 导入 CrossEncoder，用于重排序和 NLI 判断
from sentence_transformers import CrossEncoder
# 导入 hashlib 模块，用于生成唯一 ID 的哈希值
import hashlib

# 将项目根目录添加到系统路径中
import sys, os

current_abspath = os.path.abspath(__file__)  # 获取当前绝对路径
root_abspath = os.path.dirname(os.path.dirname(os.path.dirname(current_abspath)))  # 获取项目根目录绝对路径
sys.path.insert(0, root_abspath)  # 添加到系统路径中
sys.path.insert(0, os.path.dirname(current_abspath))

from base import logger, Config

conf = Config()
from rich import print
# 导入文档处理函数
from document_process import *


# core/vector_store.py
# 定义 VectorStore 类，封装向量存储和检索功能
class VectorStore:
    # 初始化方法，设置向量存储的基本参数
    def __init__(self,
                 collection_name=conf.MILVUS_COLLECTION_NAME,
                 host=conf.MILVUS_HOST,
                 port=conf.MILVUS_PORT,
                 database=conf.MILVUS_DATABASE_NAME):
        # 设置 Milvus 集合名称
        self.collection_name = collection_name
        # 设置 Milvus 主机地址
        self.host = host
        # 设置 Milvus 端口号
        self.port = port
        # 设置 Milvus 数据库名称
        self.database = database
        # 设置日志记录器
        self.logger = logger
        # 设置使用设备
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.logger.info(f'使用: {self.device} 加载模型')
        # 获取模型存储路径
        models_path = os.path.join(os.path.dirname(os.path.dirname(current_abspath)), 'models')
        # 初始化 BGE-Reranker 模型，用于重排序检索结果
        self.reranker = CrossEncoder(os.path.join(models_path, 'bge-reranker-large'), device=self.device)
        # 初始化 BGE-M3 嵌入函数，使用 CPU 设备，不启用 FP16
        self.embedding_function = BGEM3EmbeddingFunction(
            model_name_or_path=os.path.join(models_path, 'bge-m3'), use_fp16=(self.device == 'cuda'),
            device=self.device)
        # 获取稠密向量的维度
        self.dense_dim = self.embedding_function.dim["dense"]
        # 初始化 Milvus 客户端，连接到指定主机和数据库
        self.client = MilvusClient(uri=f"http://{self.host}:{self.port}", db_name=self.database)
        # 调用方法创建或加载 Milvus 集合
        self._create_or_load_collection()

    # 定义私有化方法, 创建或加载Milvus集合
    def _create_or_load_collection(self):
        # 检查指定集合是否存在
        if not self.client.has_collection(collection_name=self.collection_name):
            # 创建集合scheme, 禁止自动ID, 启动动态字段
            scheme = self.client.create_schema(auto_id=False, enable_dynamic_field=True)
            # 添加ID字段作为主键, VARCHAR类型, 最大长度100
            scheme.add_field(field_name='id', datatype=DataType.VARCHAR, is_primary=True, max_length=100)
            # 添加文本字段, VARCHAR类型, 最大长度65535
            scheme.add_field(field_name='text', datatype=DataType.VARCHAR, max_length=65535)
            # 添加稠密向量字段, FLOAT_VECTOR类型, 维度由嵌入函数指定
            scheme.add_field(field_name='dense_vector', datatype=DataType.FLOAT_VECTOR, dim=self.dense_dim)
            # 添加稀疏向量字段, SPARSE_FLOAT_VECTOR类型
            scheme.add_field(field_name='sparse_vector', datatype=DataType.SPARSE_FLOAT_VECTOR)
            # 添加父块ID字段, VARCHAR类型, 最大长度100
            scheme.add_field(field_name='parent_id', datatype=DataType.VARCHAR, max_length=100)
            # 添加父块内容字段, VARCHAR类型, 最大长度65535
            scheme.add_field(field_name='parent_content', datatype=DataType.VARCHAR, max_length=65535)
            # 添加科学类别字段, VARCHAR类型, 最大长度50
            scheme.add_field(field_name='source', datatype=DataType.VARCHAR, max_length=50)
            # 添加时间戳字段, VARCHAR类型, 最大长度50
            scheme.add_field(field_name='timestamp', datatype=DataType.VARCHAR, max_length=50)
            scheme.add_field(field_name='file_path', datatype=DataType.VARCHAR, max_length=500)

            # 创建索引参数对象
            index_params = self.client.prepare_index_params()
            # 为稠密向量字段添加IVF_FLAT索引, 度量类型为内积(IP)
            index_params.add_index(
                field_name='dense_vector',
                index_name='dense_index',
                index_type='IVF_FLAT',
                metric_type='IP',
                params={'nlist': 128}
            )

            # 为稀疏向量字段添加 SPARSE_INVERTED_INDEX索引, 度量类型为内积(IP)
            index_params.add_index(
                field_name='sparse_vector',
                index_name='sparse_index',
                index_type='SPARSE_INVERTED_INDEX',
                metric_type='IP',
                params={'drop_ratio_build': 0.2}
            )

            # 创建Milvus集合, 应用定义的Scheme 和 索引参数
            self.client.create_collection(collection_name=self.collection_name, schema=scheme,
                                          index_params=index_params)
            # 记录创建集合的日志
            self.logger.info(f'已创建集合: {self.collection_name}')
            # documents = process_documents(r"D:\Document\PythonProjects\Edu_RAG_QA\integerate_qa_system\data")
            # self.add_documents(documents)
        # 如果集合不存在
        else:
            # 记录加载集合的日志
            logger.info(f'已加载集合: {self.collection_name}')
        # 将集合加载到内存, 确保可立即查询
        self.client.load_collection(self.collection_name)

    # 定义方法, 向向量存储添加文档
    def add_documents(self, documents):
        # 提取所有文档的内容列表
        texts = [doc.page_content for doc in documents]
        # 使用BGE-M3 嵌入函数生成文档的嵌入(稠密向量, 稀疏向量)
        embeddings = self.embedding_function(texts)
        # 初始化空列表,用于存储插入的数据
        data = []
        # 遍历文档, 带上索引i
        for i, doc in enumerate(documents):
            # 生成文档内容的MD5哈希值, 作为唯一ID
            text_hash = hashlib.md5(doc.page_content.encode('utf-8')).hexdigest()
            # 初始化稀疏向量字典
            sparse_vector = {}
            # 获取第i行的稀疏向量
            row = embeddings['sparse'][[i]]
            # 获取稀疏向量的非零索引
            indices = row.indices
            # 获取稀疏向量的非零值
            values = row.data
            # 将索引和值配对,填充稀疏向量字典
            sparse_vector = {i: v for i, v in zip(indices, values)}
            # 创建数据字典包含所有字段
            data.append({
                'text': doc.page_content,
                'id': text_hash,
                'dense_vector': embeddings['dense'][i],
                'sparse_vector': sparse_vector,
                'parent_id': doc.metadata['parent_id'],
                'parent_content': doc.metadata['parent_content'],
                'source': doc.metadata.get('source', 'unknown'),
                'timestamp': doc.metadata.get('timestamp', 'unknown'),
                'file_path': doc.metadata.get('file_path', ''),
            })
            # 检查是否有数据需要插入
        if data:
            # 使用upsert操作插入数据, 覆盖重复ID
            self.client.upsert(collection_name=self.collection_name, data=data)
            # 记录插入或更新的文档数量日志
            self.logger.info(f'已插入或更新 {len(data)} 个文档')

    # 定义方法，执行混合检索并重排序
    def hybrid_search_with_rerank(self, query, k=conf.RETRIEVAL_K, source_filter=None):
        # 使用 BGE-M3 嵌入函数生成查询的嵌入
        query_embeddings = self.embedding_function([query])
        # 获取查询的稠密向量
        dense_query_vector = query_embeddings["dense"][0]
        # 初始化查询的稀疏向量字典
        sparse_query_vector = {}
        # 获取查询稀疏向量的第 0 行数据
        row = query_embeddings["sparse"][[0]]
        # 获取稀疏向量的非零值索引
        indices = row.indices
        # 获取稀疏向量的非零值
        values = row.data
        # 将索引和值配对，填充稀疏向量字典
        for idx, value in zip(indices, values):
            sparse_query_vector[idx] = value

        # 初始化过滤表达式，默认不过滤
        filter_expr = f"source == '{source_filter}'" if source_filter else ""
        # 创建稠密向量搜索请求
        dense_request = AnnSearchRequest(
            data=[dense_query_vector],
            anns_field="dense_vector",
            param={"metric_type": "IP", "params": {"nprobe": 10}},
            limit=k,
            expr=filter_expr
        )
        # 创建稀疏向量搜索请求
        sparse_request = AnnSearchRequest(
            data=[sparse_query_vector],
            anns_field="sparse_vector",
            param={"metric_type": "IP", "params": {}},
            limit=k,
            expr=filter_expr
        )

        # 创建加权排序器，稀疏向量权重 0.7，稠密向量权重 1.0
        ranker = WeightedRanker(0.7, 1.0)
        # 执行混合搜索，返回 Top-K 结果
        results = self.client.hybrid_search(
            collection_name=self.collection_name,
            reqs=[dense_request, sparse_request],
            ranker=ranker,
            limit=k,
            output_fields=["text", "parent_id", "parent_content", "source", "timestamp", "file_path"]
        )[0]

        sub_chunks = [self._doc_from_hit(hit["entity"]) for hit in results]
        
        unique_results = []
        seen_parent_ids = set()
        for chunk in sub_chunks:
            parent_id = chunk.metadata.get("parent_id")
            if parent_id and parent_id not in seen_parent_ids:
                unique_results.append(chunk)
                seen_parent_ids.add(parent_id)
        
        if len(unique_results) < 2:
            return unique_results[:conf.CANDIDATE_M]
        
        if unique_results:
            pairs = [[query, doc.page_content] for doc in unique_results]
            scores = self.reranker.predict(pairs)
            ranked_results = [doc for _, doc in sorted(zip(scores, unique_results), reverse=True)]
        else:
            ranked_results = []

        return ranked_results[:conf.CANDIDATE_M]

    def get_chunks_by_file_path(self, file_path, limit=100):
        """
        根据文件路径查询该文件的所有切片
        
        Args:
            file_path: 文件路径
            limit: 返回的最大切片数量
            
        Returns:
            list: 切片列表，每个切片包含 text, parent_content, parent_id 等信息
        """
        try:
            filter_expr = f'file_path == "{file_path}"'
            results = self.client.query(
                collection_name=self.collection_name,
                filter=filter_expr,
                output_fields=["text", "parent_id", "parent_content", "source", "timestamp", "file_path"],
                limit=limit
            )
            
            chunks = []
            for hit in results:
                chunks.append({
                    'text': hit.get('text', ''),
                    'parent_id': hit.get('parent_id', ''),
                    'parent_content': hit.get('parent_content', ''),
                    'source': hit.get('source', ''),
                    'timestamp': hit.get('timestamp', ''),
                    'file_path': hit.get('file_path', ''),
                })
            
            self.logger.info(f'文件 {file_path} 查询到 {len(chunks)} 个切片')
            return chunks
        except Exception as e:
            self.logger.error(f'查询文件切片失败: {e}')
            return []

    def _doc_from_hit(self, hit):
        return Document(
            page_content=hit.get("text"),
            metadata={
                "parent_id": hit.get("parent_id"),
                "parent_content": hit.get("parent_content"),
                "source": hit.get("source"),
                "timestamp": hit.get("timestamp"),
                "file_path": hit.get("file_path"),
            }
        )


if __name__ == '__main__':
    vector_store = VectorStore()
    # documents = process_documents(r"D:\Document\PythonProjects\Edu_RAG_QA\integerate_qa_system\data\ai")
    # vector_store.add_documents(documents)
    query = 'ai999'
    res = vector_store.hybrid_search_with_rerank(query=query, source_filter='ai')
    print(res)
    print(len(res))
