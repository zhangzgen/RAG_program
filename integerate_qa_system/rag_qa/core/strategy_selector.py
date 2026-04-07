# core/strategy_selector.py
from langchain.prompts import PromptTemplate
from openai import OpenAI

from base import Config, logger


class StrategySelector:
    VALID_STRATEGIES = ["直接检索", "假设问题检索", "子查询检索", "回溯问题检索"]

    def __init__(self):
        self.strategy_prompt_template = self._get_strategy_prompt()

    def _build_client(self):
        conf = Config()
        return OpenAI(api_key=conf.DASHSCOPE_API_KEY, base_url=conf.DASHSCOPE_BASE_URL), conf

    def call_dashscope(self, prompt):
        try:
            client, conf = self._build_client()
            completion = client.chat.completions.create(
                model=conf.LLM_MODEL,
                messages=[
                    {"role": "system", "content": "你是一个检索策略选择助手。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
            )
            if not completion.choices:
                return "直接检索"
            return (completion.choices[0].message.content or "").strip() or "直接检索"
        except Exception as exc:
            logger.error(f"Strategy selection LLM call failed: {exc}")
            return "直接检索"

    def _get_strategy_prompt(self):
        return PromptTemplate(
            template=(
                "你需要根据用户问题选择检索策略。可选值仅有：\n"
                "1. 直接检索\n"
                "2. 假设问题检索\n"
                "3. 子查询检索\n"
                "4. 回溯问题检索\n\n"
                "规则：\n"
                "- 简单明确的问题：直接检索\n"
                "- 抽象或语义模糊的问题：假设问题检索\n"
                "- 包含多个子问题的问题：子查询检索\n"
                "- 复杂长问题需先简化：回溯问题检索\n\n"
                "用户问题：{query}\n"
                "只输出一个策略名，不要解释。"
            ),
            input_variables=["query"],
        )

    def select_strategy(self, query):
        raw = self.call_dashscope(self.strategy_prompt_template.format(query=query)).strip()
        for strategy in self.VALID_STRATEGIES:
            if strategy in raw:
                logger.info(f"Strategy selected for query '{query}': {strategy}")
                return strategy

        logger.warning(f"Unexpected strategy output '{raw}', fallback to 直接检索")
        return "直接检索"


if __name__ == "__main__":
    selector = StrategySelector()
    print(selector.select_strategy("java领域的应用有哪些"))
