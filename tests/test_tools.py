import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools.base import tool, ToolDefinition
from tools.registry import ToolRegistry
from tools.shared.file_ops import file_read, file_write
from skills.data_analysis.tools.calculator import calculator


def test_tool_decorator():
    @tool(name="greet", description="打招呼")
    def greet(name: str) -> str:
        return f"Hello, {name}!"

    assert isinstance(greet, ToolDefinition)
    assert greet.name == "greet"
    result = greet.execute(name="World")
    assert result.success
    assert result.data == "Hello, World!"


def test_tool_schema():
    @tool(name="add", description="加法")
    def add(a: int, b: int) -> int:
        return a + b

    schema = add.to_schema()
    assert schema["name"] == "add"
    assert "a" in schema["parameters"]["properties"]
    assert "b" in schema["parameters"]["required"]


def test_tool_registry():
    registry = ToolRegistry()

    @tool(name="ping", description="ping")
    def ping(msg: str) -> str:
        return f"pong: {msg}"

    registry.register(ping)
    assert "ping" in registry.list_tools()
    result = registry.execute("ping", msg="test")
    assert result.success
    assert "pong" in result.data


def test_calculator():
    result = calculator.execute(expression="2 + 3 * 4")
    assert result.success
    assert result.data == "14"

    result2 = calculator.execute(expression="sqrt(144)")
    assert result2.success
    assert result2.data == "12.0"


def test_file_ops(tmp_path):
    test_file = str(tmp_path / "test.txt")
    write_result = file_write.execute(path=test_file, content="Hello Agent")
    assert write_result.success

    read_result = file_read.execute(path=test_file)
    assert read_result.success
    assert read_result.data == "Hello Agent"
