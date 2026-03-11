from typing import Optional
from .base import ToolDefinition, ToolResult
from utils.logger import logger


class ToolRegistry:
    """
    全局工具注册中心。
    - 公共 Tool（tools/shared/）启动时自动注册
    - Skill 的私有 Tool 由各 Skill 自行注册到局部池
    - 向 LLM 暴露统一的 Schema 列表
    """

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool_def: ToolDefinition) -> None:
        self._tools[tool_def.name] = tool_def
        logger.debug(f"Tool 已注册: {tool_def.name}")

    def get(self, name: str) -> Optional[ToolDefinition]:
        return self._tools.get(name)

    def execute(self, name: str, **kwargs) -> ToolResult:
        tool = self.get(name)
        if tool is None:
            return ToolResult(success=False, error=f"Tool '{name}' 不存在")
        logger.info(f"执行 Tool: {name}, args={kwargs}")
        result = tool.execute(**kwargs)
        if not result.success:
            logger.warning(f"Tool '{name}' 执行失败: {result.error}")
        return result

    def get_all_schemas(self) -> list[dict]:
        return [t.to_schema() for t in self._tools.values()]

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())

    def __len__(self) -> int:
        return len(self._tools)


# 全局单例
_global_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    return _global_registry
