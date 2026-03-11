import inspect
import functools
from typing import Callable, Any
from pydantic import BaseModel


class ToolResult(BaseModel):
    success: bool
    data: Any = None
    error: str = ""


class ToolDefinition:
    """封装一个工具函数的元数据和执行逻辑"""

    def __init__(self, fn: Callable, name: str, description: str):
        self.fn = fn
        self.name = name
        self.description = description
        self._sig = inspect.signature(fn)

    def to_schema(self) -> dict:
        """生成 LLM 可识别的 Tool JSON Schema"""
        properties = {}
        required = []
        for param_name, param in self._sig.parameters.items():
            annotation = param.annotation
            type_map = {str: "string", int: "integer", float: "number", bool: "boolean"}
            prop_type = type_map.get(annotation, "string")
            properties[param_name] = {"type": prop_type, "description": param_name}
            if param.default is inspect.Parameter.empty:
                required.append(param_name)
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

    def execute(self, **kwargs) -> ToolResult:
        try:
            result = self.fn(**kwargs)
            return ToolResult(success=True, data=result)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    def __call__(self, **kwargs):
        return self.execute(**kwargs)


def tool(name: str = "", description: str = ""):
    """
    工具注册装饰器。
    用法：
        @tool(name="web_search", description="搜索互联网")
        def web_search(query: str) -> str: ...
    """
    def decorator(fn: Callable) -> ToolDefinition:
        tool_name = name or fn.__name__
        tool_desc = description or (fn.__doc__ or "").strip()
        return ToolDefinition(fn=fn, name=tool_name, description=tool_desc)
    return decorator
