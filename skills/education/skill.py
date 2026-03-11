import re
from skills.base import BaseSkill, SkillResult
from utils.logger import logger


class EducationSkill(BaseSkill):
    """
    通用教育技能类。
    每个实例对应 claude-education-skills 中的一个 .md 文件，
    由 loader.py 动态解析并创建。

    执行流程：
    1. 用户输入填充 prompt 模板中的 {{变量}} 占位符
    2. 调用 LLM 执行填充后的 prompt
    3. 返回 SkillResult
    """

    name: str = ""
    description: str = ""
    parameters: dict = {}

    # 教育技能特有字段
    prompt_template: str = ""
    evidence_strength: str = ""
    evidence_sources: list = []
    chains_well_with: list = []
    domain: str = ""
    skill_id: str = ""
    tags: list = []

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        super().__init__()

    async def run(self, **kwargs) -> SkillResult:
        """填充 prompt 模板 → 调用 LLM → 返回结果"""
        prompt = self._fill_template(kwargs)

        if not prompt.strip():
            return SkillResult(
                success=False,
                error=f"技能 '{self.skill_id}' 的 prompt 模板为空",
            )

        try:
            from llm import get_llm_provider
            from langchain_core.messages import HumanMessage

            llm = get_llm_provider().get_model()
            response = llm.invoke([HumanMessage(content=prompt)])
            output = response.content
        except Exception as e:
            logger.error(f"EducationSkill '{self.skill_id}' LLM 调用失败: {e}")
            return SkillResult(success=False, error=str(e))

        return SkillResult(
            success=True,
            data={
                "output": output,
                "skill_id": self.skill_id,
                "evidence_strength": self.evidence_strength,
            },
            metadata={
                "domain": self.domain,
                "chains_well_with": self.chains_well_with,
                "tags": self.tags,
                "input_args": kwargs,
            },
        )

    def _fill_template(self, kwargs: dict) -> str:
        """
        将 {{variable}} 替换为实际值。
        未提供的字段填充为 'not provided'，
        与原始 prompt 模板中的 "if not provided" 逻辑配合。
        """
        prompt = self.prompt_template
        placeholders = re.findall(r"\{\{(\w+)\}\}", prompt)
        for key in placeholders:
            value = kwargs.get(key, "not provided")
            if isinstance(value, (list, tuple)):
                value = ", ".join(str(v) for v in value)
            prompt = prompt.replace(f"{{{{{key}}}}}", str(value))
        return prompt

    def to_tool_schema(self) -> dict:
        """扩展父类 schema，在 description 中注入证据强度标签"""
        schema = super().to_tool_schema()
        schema["description"] = (
            f"[edu|{self.evidence_strength}] {self.description}"
        )
        return schema
