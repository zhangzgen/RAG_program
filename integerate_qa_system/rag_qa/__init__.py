import sys, os

rag_qa_path = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, rag_qa_path)
from core.vector_store import VectorStore
# from core.rag_system import RAGSystem  # 没有考虑历史对话和stream流式输出
from core.new_rag_system import RAGSystem  # 考虑历史对话和stream流式输出
