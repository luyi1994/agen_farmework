from .registry import ToolRegistry, get_tool_registry
from .base import tool, ToolDefinition, ToolResult


def load_shared_tools() -> None:
    """启动时自动加载 tools/shared/ 下的所有公共工具"""
    from tools.shared.web_search import web_search
    from tools.shared.file_ops import file_read, file_write

    registry = get_tool_registry()
    for t in [web_search, file_read, file_write]:
        registry.register(t)


__all__ = ["ToolRegistry", "get_tool_registry", "tool", "ToolDefinition", "ToolResult", "load_shared_tools"]
