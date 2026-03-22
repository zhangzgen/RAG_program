import time
import json
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any


@dataclass
class TraceStep:
    name: str
    executed: bool = False
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    status: str = 'pending'
    input: Optional[Any] = None
    output: Optional[Any] = None
    error: Optional[str] = None

    def start(self):
        self.executed = True
        self.start_time = time.time()
        self.status = 'running'

    def finish(self, output: Any = None, status: str = 'success'):
        self.end_time = time.time()
        self.duration_ms = round((self.end_time - self.start_time) * 1000, 2) if self.start_time else None
        self.output = output
        self.status = status

    def fail(self, error: str):
        self.end_time = time.time()
        self.duration_ms = round((self.end_time - self.start_time) * 1000, 2) if self.start_time else None
        self.error = error
        self.status = 'failed'

    def skip(self, reason: str = None):
        self.executed = False
        self.status = 'skipped'
        if reason:
            self.error = reason

    def to_dict(self):
        return {
            'name': self.name,
            'executed': self.executed,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration_ms': self.duration_ms,
            'status': self.status,
            'input': self.input,
            'output': self.output,
            'error': self.error
        }


@dataclass
class FqaTrace(TraceStep):
    name: str = 'fqa_search'
    score: Optional[float] = None
    matched: bool = False

    def to_dict(self):
        d = super().to_dict()
        d['score'] = self.score
        d['matched'] = self.matched
        return d


@dataclass
class QueryClassifyTrace(TraceStep):
    name: str = 'query_classification'
    category: Optional[str] = None
    confidence: Optional[float] = None

    def to_dict(self):
        d = super().to_dict()
        d['category'] = self.category
        d['confidence'] = self.confidence
        return d


@dataclass
class StrategySelectTrace(TraceStep):
    name: str = 'strategy_selection'
    strategy: Optional[str] = None

    def to_dict(self):
        d = super().to_dict()
        d['strategy'] = self.strategy
        return d


@dataclass
class RetrievalResult:
    content: str
    score: float
    source: Optional[str] = None
    file_path: Optional[str] = None
    parent_id: Optional[str] = None


@dataclass
class VectorRetrievalTrace(TraceStep):
    name: str = 'vector_retrieval'
    strategy_used: Optional[str] = None
    retrieval_k: Optional[int] = None
    candidate_m: Optional[int] = None
    results: List[Dict] = field(default_factory=list)
    total_results: int = 0

    def to_dict(self):
        d = super().to_dict()
        d['strategy_used'] = self.strategy_used
        d['retrieval_k'] = self.retrieval_k
        d['candidate_m'] = self.candidate_m
        d['results'] = self.results
        d['total_results'] = self.total_results
        return d


@dataclass
class LlmTrace(TraceStep):
    name: str = 'llm_generation'
    model: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    is_thinking_model: bool = False
    thinking_content: Optional[str] = None

    def to_dict(self):
        d = super().to_dict()
        d['model'] = self.model
        d['prompt_tokens'] = self.prompt_tokens
        d['completion_tokens'] = self.completion_tokens
        d['total_tokens'] = self.total_tokens
        d['is_thinking_model'] = self.is_thinking_model
        d['thinking_content'] = self.thinking_content
        return d


@dataclass
class TraceData:
    query: str
    session_id: Optional[str] = None
    source_filter: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    total_duration_ms: Optional[float] = None
    final_answer: Optional[str] = None
    answer_source: Optional[str] = None
    
    fqa: FqaTrace = field(default_factory=FqaTrace)
    query_classify: QueryClassifyTrace = field(default_factory=QueryClassifyTrace)
    strategy_select: StrategySelectTrace = field(default_factory=StrategySelectTrace)
    vector_retrieval: VectorRetrievalTrace = field(default_factory=VectorRetrievalTrace)
    llm: LlmTrace = field(default_factory=LlmTrace)

    def finish(self, answer: str, source: str):
        self.end_time = time.time()
        self.total_duration_ms = round((self.end_time - self.start_time) * 1000, 2)
        self.final_answer = answer
        self.answer_source = source

    def to_dict(self) -> Dict:
        return {
            'query': self.query,
            'session_id': self.session_id,
            'source_filter': self.source_filter,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'total_duration_ms': self.total_duration_ms,
            'final_answer': self.final_answer,
            'answer_source': self.answer_source,
            'fqa': self.fqa.to_dict(),
            'query_classify': self.query_classify.to_dict(),
            'strategy_select': self.strategy_select.to_dict(),
            'vector_retrieval': self.vector_retrieval.to_dict(),
            'llm': self.llm.to_dict()
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)

    @classmethod
    def from_dict(cls, data: Dict) -> 'TraceData':
        trace = cls(
            query=data.get('query'),
            session_id=data.get('session_id'),
            source_filter=data.get('source_filter'),
            start_time=data.get('start_time', time.time()),
            end_time=data.get('end_time'),
            total_duration_ms=data.get('total_duration_ms'),
            final_answer=data.get('final_answer'),
            answer_source=data.get('answer_source')
        )
        
        if 'fqa' in data:
            fqa_data = data['fqa']
            trace.fqa = FqaTrace(**{k: v for k, v in fqa_data.items() if k in FqaTrace.__dataclass_fields__})
        
        if 'query_classify' in data:
            qc_data = data['query_classify']
            trace.query_classify = QueryClassifyTrace(**{k: v for k, v in qc_data.items() if k in QueryClassifyTrace.__dataclass_fields__})
        
        if 'strategy_select' in data:
            ss_data = data['strategy_select']
            trace.strategy_select = StrategySelectTrace(**{k: v for k, v in ss_data.items() if k in StrategySelectTrace.__dataclass_fields__})
        
        if 'vector_retrieval' in data:
            vr_data = data['vector_retrieval']
            trace.vector_retrieval = VectorRetrievalTrace(**{k: v for k, v in vr_data.items() if k in VectorRetrievalTrace.__dataclass_fields__})
        
        if 'llm' in data:
            llm_data = data['llm']
            trace.llm = LlmTrace(**{k: v for k, v in llm_data.items() if k in LlmTrace.__dataclass_fields__})
        
        return trace


if __name__ == '__main__':
    trace = TraceData(query="AI是什么", session_id="test-123")
    
    trace.fqa.start()
    time.sleep(0.1)
    trace.fqa.finish(output="AI是人工智能", status='success')
    trace.fqa.score = 0.95
    trace.fqa.matched = True
    
    print(trace.to_json())
