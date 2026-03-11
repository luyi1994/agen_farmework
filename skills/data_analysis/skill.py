from skills.base import BaseSkill, SkillResult
from skills.data_analysis.tools.calculator import calculator
from utils.logger import logger


class DataAnalysisSkill(BaseSkill):
    """数据分析 Skill：读取文件 + 统计计算 + 生成分析报告"""

    name = "data_analysis"
    description = "读取数据文件，执行统计计算，生成数据分析报告"
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "数据文件路径（CSV/TXT/JSON）"},
            "question": {"type": "string", "description": "分析问题，如'统计各列均值'"},
        },
        "required": ["file_path", "question"],
    }

    def _register_private_tools(self):
        self._private_registry.register(calculator)

    async def run(self, file_path: str, question: str) -> SkillResult:
        logger.info(f"DataAnalysisSkill 开始: file={file_path}")

        # 1. 读取文件
        file_content = self._execute_tool("file_read", path=file_path)

        # 2. LLM 分析并生成计算表达式
        from llm import get_llm_provider
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = get_llm_provider().get_model()
        analysis_prompt = (
            f"你是一个数据分析助手。根据以下数据文件内容回答分析问题。\n\n"
            f"文件内容：\n{file_content[:4000]}\n\n"
            f"分析问题：{question}\n\n"
            f"请给出分析结论和报告。"
        )
        response = llm.invoke([
            SystemMessage(content="你是专业的数据分析师，给出简洁、准确的分析报告。"),
            HumanMessage(content=analysis_prompt),
        ])
        report = response.content

        # 3. 保存报告
        output_path = file_path.replace(".", "_report.").rsplit(".", 1)[0] + "_report.md"
        self._execute_tool("file_write", path=output_path, content=f"# 数据分析报告\n\n**问题：** {question}\n\n{report}")

        return SkillResult(
            success=True,
            data={"report": report, "output_file": output_path},
            metadata={"file": file_path, "question": question},
        )
