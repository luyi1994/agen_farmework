from skills.base import BaseSkill, SkillResult
from skills.research.tools.content_extractor import content_extractor
from utils.logger import logger


class ResearchSkill(BaseSkill):
    """
    深度调研 Skill。
    流程：多轮搜索 → 提取网页正文 → LLM 摘要整合 → 存入长期记忆
    """

    name = "research"
    description = "对指定主题进行多轮深度网络调研，返回结构化摘要报告并存入长期记忆"
    parameters = {
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "调研主题"},
            "max_rounds": {"type": "integer", "description": "最大搜索轮数，默认 2"},
        },
        "required": ["topic"],
    }

    def _register_private_tools(self):
        self._private_registry.register(content_extractor)

    async def run(self, topic: str, max_rounds: int = 2) -> SkillResult:
        logger.info(f"ResearchSkill 开始: topic={topic}, max_rounds={max_rounds}")
        all_content = []

        # 1. 多轮搜索
        queries = [topic, f"{topic} latest news 2026", f"{topic} research overview"]
        for i, query in enumerate(queries[:max_rounds]):
            try:
                result = self._execute_tool("web_search", query=query)
                all_content.append(f"=== 搜索轮次 {i+1}: {query} ===\n{result}")
                logger.debug(f"搜索轮次 {i+1} 完成")
            except Exception as e:
                logger.warning(f"搜索轮次 {i+1} 失败: {e}")

        if not all_content:
            return SkillResult(success=False, error="所有搜索轮次均失败")

        combined = "\n\n".join(all_content)

        # 2. 使用 LLM 摘要整合（通过注入的 LLM 调用）
        summary = self._summarize_with_llm(topic, combined)

        # 3. 存入长期记忆
        memory_id = self._save_to_memory(topic, summary)

        return SkillResult(
            success=True,
            data={"summary": summary, "memory_id": memory_id},
            metadata={"topic": topic, "rounds": min(max_rounds, len(queries))},
        )

    def _summarize_with_llm(self, topic: str, content: str) -> str:
        from llm import get_llm_provider
        from langchain_core.messages import HumanMessage

        llm = get_llm_provider().get_model()
        prompt = (
            f"请基于以下搜索结果，对主题「{topic}」生成一份结构清晰的中文摘要报告（600字以内）：\n\n"
            f"{content[:6000]}"
        )
        response = llm.invoke([HumanMessage(content=prompt)])
        return response.content

    def _save_to_memory(self, topic: str, summary: str) -> str:
        from memory.long_term import LongTermMemory
        mem = LongTermMemory()
        return mem.save(summary, metadata={"topic": topic, "skill": "research"})
