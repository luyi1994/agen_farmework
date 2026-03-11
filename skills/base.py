from abc import ABC, abstractmethod
from typing import Any
from pydantic import BaseModel

from tools.registry import ToolRegistry, get_tool_registry
from utils.logger import logger


class SkillResult(BaseModel):
    success: bool
    data: Any = None
    error: str = ""
    metadata: dict = {}


class BaseSkill(ABC):
    """
    Skill 抽象基类。

    每个 Skill 是一个自包含的多步骤能力包：
    - 可调用自己 skills/<name>/tools/ 下的私有工具
    - 可 fallback 到全局公共 ToolRegistry（tools/shared/）
    - 对 LLM 暴露为一个标准 Tool Schema
    """

    name: str = ""
    description: str = ""
    parameters: dict = {}  # JSON Schema 参数定义

    def __init__(self):
        self._private_registry = ToolRegistry()  # 私有工具池
        self._global_registry = get_tool_registry()  # 公共工具池
        self._register_private_tools()

    def _register_private_tools(self):
        """子类重写此方法以注册自己的私有工具"""
        pass

    def _execute_tool(self, tool_name: str, **kwargs):
        """优先查找私有工具，再 fallback 到全局公共工具"""
        tool = self._private_registry.get(tool_name)
        if tool:
            result = tool.execute(**kwargs)
        else:
            result = self._global_registry.execute(tool_name, **kwargs)

        if not result.success:
            raise RuntimeError(f"Tool '{tool_name}' 执行失败: {result.error}")
        return result.data

    @abstractmethod
    async def run(self, **kwargs) -> SkillResult:
        """Skill 主逻辑，子类必须实现"""

    def to_tool_schema(self) -> dict:
        """将 Skill 暴露为 LLM 可识别的 Tool Schema（与 Tool 格式相同）"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters or {
                "type": "object",
                "properties": {},
                "required": [],
            },
        }
