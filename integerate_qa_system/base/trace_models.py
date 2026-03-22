"""
执行链路数据模型体系
用于记录和追踪系统各组件的执行情况
"""

import json
import time
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod


class BaseTrace(ABC):
    """基础Trace模型类"""
    
    def __init__(self):
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.is_executed: bool = False
        self.content: str = ""
        self.duration_ms: int = 0
        self.error: Optional[str] = None
    
    def start(self):
        """开始执行，记录开始时间"""
        self.start_time = time.time()
        self.is_executed = False
    
    def end(self, content: str = "", error: str = None):
        """结束执行，记录结束时间并计算执行时长"""
        self.end_time = time.time()
        self.content = content
        self.is_executed = True
        self.error = error
        if self.start_time:
            self.duration_ms = int((self.end_time - self.start_time) * 1000)
    
    def calculate_duration(self) -> int:
        """计算执行时长（毫秒）"""
        if self.start_time and self.end_time:
            return int((self.end_time - self.start_time) * 1000)
        return 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            'start_time': datetime.fromtimestamp(self.start_time).isoformat() if self.start_time else None,
            'end_time': datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None,
            'is_executed': self.is_executed,
            'content': self.content,
            'duration_ms': self.duration_ms,
            'error': self.error
        }
        return result
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


class RedisTrace(BaseTrace):
    """Redis操作链路模型"""
    
    def __init__(self):
        super().__init__()
        self.key: str = ""
        self.operation_type: str = ""
        self.result_size: int = 0
        self.ttl: Optional[int] = None
    
    def start(self, key: str = "", operation_type: str = ""):
        """开始Redis操作"""
        super().start()
        self.key = key
        self.operation_type = operation_type
    
    def end(self, content: str = "", result_size: int = 0, ttl: int = None, error: str = None):
        """结束Redis操作"""
        super().end(content, error)
        self.result_size = result_size
        self.ttl = ttl
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = super().to_dict()
        result.update({
            'key': self.key,
            'operation_type': self.operation_type,
            'result_size': self.result_size,
            'ttl': self.ttl
        })
        return result


class MysqlTrace(BaseTrace):
    """MySQL数据库操作链路模型"""
    
    def __init__(self):
        super().__init__()
        self.sql_statement: str = ""
        self.affected_rows: int = 0
        self.query_type: str = ""
        self.table_name: str = ""
    
    def start(self, sql_statement: str = "", query_type: str = "", table_name: str = ""):
        """开始MySQL操作"""
        super().start()
        self.sql_statement = sql_statement
        self.query_type = query_type
        self.table_name = table_name
    
    def end(self, content: str = "", affected_rows: int = 0, error: str = None):
        """结束MySQL操作"""
        super().end(content, error)
        self.affected_rows = affected_rows
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = super().to_dict()
        result.update({
            'sql_statement': self.sql_statement,
            'affected_rows': self.affected_rows,
            'query_type': self.query_type,
            'table_name': self.table_name
        })
        return result


class MilvusTrace(BaseTrace):
    """Milvus向量数据库操作链路模型"""
    
    def __init__(self):
        super().__init__()
        self.collection_name: str = ""
        self.operation_type: str = ""
        self.vector_count: int = 0
        self.search_params: Dict[str, Any] = {}
        self.top_k: int = 0
        self.rerank_score: Optional[float] = None
    
    def start(self, collection_name: str = "", operation_type: str = ""):
        """开始Milvus操作"""
        super().start()
        self.collection_name = collection_name
        self.operation_type = operation_type
    
    def end(self, content: str = "", vector_count: int = 0, search_params: Dict = None, 
            top_k: int = 0, rerank_score: float = None, error: str = None):
        """结束Milvus操作"""
        super().end(content, error)
        self.vector_count = vector_count
        self.search_params = search_params or {}
        self.top_k = top_k
        self.rerank_score = rerank_score
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = super().to_dict()
        result.update({
            'collection_name': self.collection_name,
            'operation_type': self.operation_type,
            'vector_count': self.vector_count,
            'search_params': self.search_params,
            'top_k': self.top_k,
            'rerank_score': self.rerank_score
        })
        return result


class LlmTrace(BaseTrace):
    """大语言模型调用链路模型"""
    
    def __init__(self):
        super().__init__()
        self.model_name: str = ""
        self.prompt_tokens: int = 0
        self.completion_tokens: int = 0
        self.total_tokens: int = 0
        self.temperature: float = 0.0
        self.is_thinking: bool = False
        self.thinking_content: str = ""
    
    def start(self, model_name: str = "", temperature: float = 0.0, is_thinking: bool = False):
        """开始LLM调用"""
        super().start()
        self.model_name = model_name
        self.temperature = temperature
        self.is_thinking = is_thinking
    
    def end(self, content: str = "", prompt_tokens: int = 0, completion_tokens: int = 0,
            thinking_content: str = "", error: str = None):
        """结束LLM调用"""
        super().end(content, error)
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = prompt_tokens + completion_tokens
        self.thinking_content = thinking_content
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = super().to_dict()
        result.update({
            'model_name': self.model_name,
            'prompt_tokens': self.prompt_tokens,
            'completion_tokens': self.completion_tokens,
            'total_tokens': self.total_tokens,
            'temperature': self.temperature,
            'is_thinking': self.is_thinking,
            'thinking_content': self.thinking_content
        })
        return result


class SessionTrace:
    """整体Trace容器模型"""
    
    def __init__(self, user_query: str = ""):
        self.trace_id: str = str(uuid.uuid4())
        self.user_query: str = user_query
        self.timestamp: str = datetime.now().isoformat()
        self.start_time: float = time.time()
        self.end_time: Optional[float] = None
        self.total_duration_ms: int = 0
        
        self.redis_traces: List[RedisTrace] = []
        self.mysql_traces: List[MysqlTrace] = []
        self.milvus_traces: List[MilvusTrace] = []
        self.llm_traces: List[LlmTrace] = []
        
        self.final_answer: str = ""
        self.status: str = "started"
        self.error: Optional[str] = None
    
    def add_redis_trace(self, trace: RedisTrace):
        """添加Redis链路数据"""
        self.redis_traces.append(trace)
    
    def add_mysql_trace(self, trace: MysqlTrace):
        """添加MySQL链路数据"""
        self.mysql_traces.append(trace)
    
    def add_milvus_trace(self, trace: MilvusTrace):
        """添加Milvus链路数据"""
        self.milvus_traces.append(trace)
    
    def add_llm_trace(self, trace: LlmTrace):
        """添加LLM链路数据"""
        self.llm_traces.append(trace)
    
    def create_redis_trace(self) -> RedisTrace:
        """创建并返回一个新的Redis链路对象"""
        trace = RedisTrace()
        self.add_redis_trace(trace)
        return trace
    
    def create_mysql_trace(self) -> MysqlTrace:
        """创建并返回一个新的MySQL链路对象"""
        trace = MysqlTrace()
        self.add_mysql_trace(trace)
        return trace
    
    def create_milvus_trace(self) -> MilvusTrace:
        """创建并返回一个新的Milvus链路对象"""
        trace = MilvusTrace()
        self.add_milvus_trace(trace)
        return trace
    
    def create_llm_trace(self) -> LlmTrace:
        """创建并返回一个新的LLM链路对象"""
        trace = LlmTrace()
        self.add_llm_trace(trace)
        return trace
    
    def finalize(self, final_answer: str = "", error: str = None):
        """完成会话链路记录"""
        self.end_time = time.time()
        self.total_duration_ms = int((self.end_time - self.start_time) * 1000)
        self.final_answer = final_answer
        self.error = error
        self.status = "completed" if not error else "failed"
    
    def validate(self) -> Dict[str, Any]:
        """验证数据完整性"""
        validation_result = {
            'is_valid': True,
            'missing_fields': [],
            'warnings': []
        }
        
        if not self.trace_id:
            validation_result['is_valid'] = False
            validation_result['missing_fields'].append('trace_id')
        
        if not self.user_query:
            validation_result['warnings'].append('user_query is empty')
        
        for i, trace in enumerate(self.redis_traces):
            if not trace.is_executed:
                validation_result['warnings'].append(f'redis_traces[{i}] not executed')
        
        for i, trace in enumerate(self.mysql_traces):
            if not trace.is_executed:
                validation_result['warnings'].append(f'mysql_traces[{i}] not executed')
        
        for i, trace in enumerate(self.milvus_traces):
            if not trace.is_executed:
                validation_result['warnings'].append(f'milvus_traces[{i}] not executed')
        
        for i, trace in enumerate(self.llm_traces):
            if not trace.is_executed:
                validation_result['warnings'].append(f'llm_traces[{i}] not executed')
        
        return validation_result
    
    def get_summary(self) -> Dict[str, Any]:
        """获取链路摘要信息"""
        return {
            'trace_id': self.trace_id,
            'total_duration_ms': self.total_duration_ms,
            'redis_count': len(self.redis_traces),
            'mysql_count': len(self.mysql_traces),
            'milvus_count': len(self.milvus_traces),
            'llm_count': len(self.llm_traces),
            'redis_total_ms': sum(t.duration_ms for t in self.redis_traces),
            'mysql_total_ms': sum(t.duration_ms for t in self.mysql_traces),
            'milvus_total_ms': sum(t.duration_ms for t in self.milvus_traces),
            'llm_total_ms': sum(t.duration_ms for t in self.llm_traces),
            'status': self.status
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'trace_id': self.trace_id,
            'user_query': self.user_query,
            'timestamp': self.timestamp,
            'start_time': datetime.fromtimestamp(self.start_time).isoformat(),
            'end_time': datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None,
            'total_duration_ms': self.total_duration_ms,
            'final_answer': self.final_answer,
            'status': self.status,
            'error': self.error,
            'summary': self.get_summary(),
            'redis_traces': [t.to_dict() for t in self.redis_traces],
            'mysql_traces': [t.to_dict() for t in self.mysql_traces],
            'milvus_traces': [t.to_dict() for t in self.milvus_traces],
            'llm_traces': [t.to_dict() for t in self.llm_traces]
        }
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    def to_compact_json(self) -> str:
        """转换为紧凑的JSON字符串（用于数据库存储）"""
        return json.dumps(self.to_dict(), ensure_ascii=False)


class TraceContext:
    """Trace上下文管理器，用于简化链路记录"""
    
    def __init__(self, session_trace: SessionTrace, trace_type: str, **kwargs):
        self.session_trace = session_trace
        self.trace_type = trace_type
        self.trace = None
        self.kwargs = kwargs
    
    def __enter__(self):
        if self.trace_type == 'redis':
            self.trace = self.session_trace.create_redis_trace()
            self.trace.start(**self.kwargs)
        elif self.trace_type == 'mysql':
            self.trace = self.session_trace.create_mysql_trace()
            self.trace.start(**self.kwargs)
        elif self.trace_type == 'milvus':
            self.trace = self.session_trace.create_milvus_trace()
            self.trace.start(**self.kwargs)
        elif self.trace_type == 'llm':
            self.trace = self.session_trace.create_llm_trace()
            self.trace.start(**self.kwargs)
        return self.trace
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.trace.end(error=str(exc_val))
        return False
