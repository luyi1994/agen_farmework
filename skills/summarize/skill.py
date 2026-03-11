import json
from skills.base import BaseSkill, SkillResult
from skills.summarize.tools.text_chunker import text_chunker
from utils.logger import logger


class SummarizeSkill(BaseSkill):
    """长文本分段摘要 Skill"""

    name = "summarize"
    description = "对长文本进行自动分段摘要，返回精简后的摘要内容"
    parameters = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "需要摘要的长文本"},
            "max_length": {"type": "integer", "description": "摘要目标字数，默认 300"},
        },
        "required": ["text"],
    }

    def _register_private_tools(self):
        self._private_registry.register(text_chunker)

    async def run(self, text: str, max_length: int = 300) -> SkillResult:
        logger.info(f"SummarizeSkill 开始: text_len={len(text)}")

        # 1. 分块
        chunks_json = self._execute_tool("text_chunker", text=text, chunk_size=1500)
        chunks = json.loads(chunks_json)
        logger.debug(f"文本分为 {len(chunks)} 块")

        # 2. 逐块摘要后合并
        from llm import get_llm_provider
        from langchain_core.messages import HumanMessage

        llm = get_llm_provider().get_model()
        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            prompt = f"请用 {max_length // max(len(chunks), 1)} 字以内总结以下内容：\n\n{chunk}"
            resp = llm.invoke([HumanMessage(content=prompt)])
            chunk_summaries.append(resp.content)

        final_summary = "\n\n".join(chunk_summaries)
        if len(chunks) > 1:
            merge_prompt = f"请将以下分段摘要合并为一篇连贯的总结（{max_length}字以内）：\n\n{final_summary}"
            final_summary = llm.invoke([HumanMessage(content=merge_prompt)]).content

        return SkillResult(
            success=True,
            data={"summary": final_summary},
            metadata={"original_length": len(text), "chunks": len(chunks)},
        )
