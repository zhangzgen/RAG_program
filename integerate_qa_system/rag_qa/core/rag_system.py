# core/rag_system.py 源码

import time
import sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from prompts import RAGPrompts

project_root_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root_path)
from base import logger, Config
from base.trace_models import SessionTrace, MilvusTrace, LlmTrace
from query_classifier import QueryClassifier
from strategy_selector import StrategySelector

core_path = os.path.dirname(os.path.abspath(__file__))
from vector_store import VectorStore
from strategy_selector import StrategySelector

conf = Config()


class RAGSystem:
    def __init__(self, vector_store, llm):
        self.vector_store = vector_store
        self.llm = llm
        self.rag_prompt = RAGPrompts.rag_prompt()
        classifier_path = os.path.join(core_path, 'bert_query_classifier')
        self.query_classifier = QueryClassifier(model_path=classifier_path)
        self.strategy_selector = StrategySelector()

    def _retrieve_with_hyde(self, query, source_filter=None):
        logger.info(f"使用 HyDE 策略进行检索 (查询: '{query}')")
        hyde_prompt_template = RAGPrompts.hyde_prompt()
        try:
            hypo_answer = self.llm(hyde_prompt_template.format(query=query)).strip()
            logger.info(f"HyDE 生成的假设答案: '{hypo_answer}'")
            return self.vector_store.hybrid_search_with_rerank(
                hypo_answer, k=conf.RETRIEVAL_K, source_filter=source_filter
            )
        except Exception as e:
            logger.error(f"HyDE 策略执行失败: {e}")
            return []

    def _retrieve_with_subqueries(self, query, source_filter=None):
        logger.info(f"使用子查询策略进行检索 (查询: '{query}')")
        subquery_prompt_template = RAGPrompts.subquery_prompt()
        try:
            subqueries_text = self.llm(subquery_prompt_template.format(query=query)).strip()
            subqueries = [q.strip() for q in subqueries_text.split("\n") if q.strip()]
            logger.info(f"生成的子查询: {subqueries}")
            if not subqueries:
                logger.warning("未能生成有效的子查询")
                return []

            all_docs = []
            for sub_q in subqueries:
                docs = self.vector_store.hybrid_search_with_rerank(
                    sub_q, k=conf.RETRIEVAL_K // 2, source_filter=source_filter
                )
                all_docs.extend(docs)
                logger.info(f"子查询 '{sub_q}' 检索到 {len(docs)} 个文档")

            unique_docs_dict = {doc.page_content: doc for doc in all_docs}
            unique_docs = list(unique_docs_dict.values())

            logger.info(f"所有子查询共检索到 {len(all_docs)} 个文档, 去重后剩 {len(unique_docs)} 个")
            return unique_docs

        except Exception as e:
            logger.error(f"子查询策略执行失败: {e}")
            return []

    def _retrieve_with_backtracking(self, query, source_filter=None):
        logger.info(f"使用回溯问题策略进行检索 (查询: '{query}')")
        backtrack_prompt_template = RAGPrompts.backtracking_prompt()
        try:
            simplified_query = self.llm(backtrack_prompt_template.format(query=query)).strip()
            logger.info(f"生成的回溯问题: '{simplified_query}'")
            return self.vector_store.hybrid_search_with_rerank(
                simplified_query, k=conf.RETRIEVAL_K, source_filter=source_filter
            )
        except Exception as e:
            logger.error(f"回溯问题策略执行失败: {e}")
            return []

    def retrieve_and_merge(self, query, source_filter=None, strategy=None):
        if not strategy:
            strategy = self.strategy_selector.select_strategy(query)

        ranked_sub_chunks = []
        if strategy == "回溯问题检索":
            ranked_sub_chunks = self._retrieve_with_backtracking(query, source_filter=source_filter)
        elif strategy == "子查询检索":
            ranked_sub_chunks = self._retrieve_with_subqueries(query)
        elif strategy == "假设问题检索":
            ranked_sub_chunks = self._retrieve_with_hyde(query)
        else:
            logger.info(f"使用直接检索策略 (查询: '{query}')")
            ranked_sub_chunks = self.vector_store.hybrid_search_with_rerank(
                query, k=conf.RETRIEVAL_K, source_filter=source_filter
            )

        logger.info(f"策略 '{strategy}' 检索到 {len(ranked_sub_chunks)} 个候选文档")
        final_context_docs = ranked_sub_chunks[:conf.CANDIDATE_M]
        logger.info(f"最终选取 {len(final_context_docs)} 个文档作为上下文")
        return final_context_docs

    def generate_answer(self, query, source_filter=None, session_trace=None):
        """生成答案，支持执行链路追踪"""
        start_time = time.time()
        logger.info(f"开始处理查询: '{query}', 学科过滤: {source_filter}")

        query_category = self.query_classifier.predict_model(query)
        logger.info(f"查询分类结果：{query_category} (查询: '{query}')")

        if query_category == "通用知识":
            logger.info("查询为通用知识，直接调用 LLM")
            prompt_input = self.rag_prompt.format(
                context="", question=query, phone=conf.CUSTOMER_SERVICE_PHONE
            )
            
            llm_trace = None
            if session_trace:
                llm_trace = session_trace.create_llm_trace()
                llm_trace.start(model_name=conf.LLM_MODEL, temperature=0.0, is_thinking=conf.is_thinking_model())
            
            try:
                answer = self.llm(prompt_input)
                if llm_trace:
                    llm_trace.end(content="通用知识回答生成完成")
            except Exception as e:
                logger.error(f"直接调用 LLM 失败: {e}")
                answer = f"抱歉，处理您的通用知识问题时出错。请联系人工客服：{conf.CUSTOMER_SERVICE_PHONE}"
                if llm_trace:
                    llm_trace.end(error=str(e))
            
            processing_time = time.time() - start_time
            logger.info(f"通用知识查询处理完成 (耗时: {processing_time:.2f}s, 查询: '{query}')")
            return answer

        logger.info("查询为专业咨询，执行 RAG 流程")
        strategy = self.strategy_selector.select_strategy(query)

        milvus_trace = None
        if session_trace:
            milvus_trace = session_trace.create_milvus_trace()
            milvus_trace.start(collection_name=conf.MILVUS_COLLECTION_NAME, operation_type="hybrid_search_with_rerank")

        context_docs = self.retrieve_and_merge(query, source_filter=source_filter, strategy=strategy)

        if milvus_trace:
            milvus_trace.end(
                content=f"检索到 {len(context_docs)} 个文档块",
                vector_count=len(context_docs),
                top_k=conf.RETRIEVAL_K
            )

        if context_docs:
            context = "\n\n".join([doc.page_content for doc in context_docs])
            logger.info(f"构建上下文完成，包含 {len(context_docs)} 个文档块")
        else:
            context = ""
            logger.info("未检索到相关文档，上下文为空")

        prompt_input = self.rag_prompt.format(
            context=context, question=query, phone=conf.CUSTOMER_SERVICE_PHONE
        )

        llm_trace = None
        if session_trace:
            llm_trace = session_trace.create_llm_trace()
            llm_trace.start(model_name=conf.LLM_MODEL, temperature=0.0, is_thinking=conf.is_thinking_model())

        try:
            answer = self.llm(prompt_input)
            if llm_trace:
                llm_trace.end(content="RAG回答生成完成")
        except Exception as e:
            logger.error(f"调用 LLM 生成最终答案失败: {e}")
            answer = f"抱歉，处理您的专业咨询问题时出错。请联系人工客服：{conf.CUSTOMER_SERVICE_PHONE}"
            if llm_trace:
                llm_trace.end(error=str(e))

        processing_time = time.time() - start_time
        logger.info(f"查询处理完成 (耗时: {processing_time:.2f}s, 查询: '{query}')")
        return answer


if __name__ == '__main__':
    store = VectorStore()
    rag_system = RAGSystem(vector_store=store, llm=StrategySelector().call_dashscope)
    print(rag_system._retrieve_with_subqueries("AI和JAVA的区别是什么?"))
