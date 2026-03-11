from skills.base import BaseSkill, SkillResult
from skills.write_report.tools.formatter import markdown_formatter
from utils.logger import logger


class WriteReportSkill(BaseSkill):
    """生成报告 Skill：调研主题 → 格式化 → 保存文件"""

    name = "write_report"
    description = "对指定主题进行调研后生成结构化 Markdown 报告并保存到文件"
    parameters = {
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "报告主题"},
            "output_path": {"type": "string", "description": "报告保存路径，默认 ./output/<topic>.md"},
        },
        "required": ["topic"],
    }

    def _register_private_tools(self):
        self._private_registry.register(markdown_formatter)

    async def run(self, topic: str, output_path: str = "") -> SkillResult:
        logger.info(f"WriteReportSkill 开始: topic={topic}")

        # 1. 搜索调研内容
        search_result = self._execute_tool("web_search", query=f"{topic} comprehensive overview")

        # 2. LLM 生成报告正文
        from llm import get_llm_provider
        from langchain_core.messages import HumanMessage

        llm = get_llm_provider().get_model()
        prompt = (
            f"基于以下搜索结果，为主题「{topic}」撰写一篇结构清晰的报告。\n"
            f"要求：包含背景、现状、关键发现、结论四个部分，共 800 字左右。\n\n"
            f"搜索内容：\n{search_result[:5000]}"
        )
        response = llm.invoke([HumanMessage(content=prompt)])
        body = response.content

        # 3. 格式化为 Markdown
        formatted = self._execute_tool(
            "markdown_formatter", title=topic, content=body
        )

        # 4. 写入文件
        if not output_path:
            safe_name = topic.replace(" ", "_").replace("/", "_")[:50]
            output_path = f"./output/{safe_name}.md"

        self._execute_tool("file_write", path=output_path, content=formatted)
        logger.info(f"报告已生成: {output_path}")

        return SkillResult(
            success=True,
            data={"report": formatted, "output_path": output_path},
            metadata={"topic": topic},
        )
