import pytest
import asyncio
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.mark.asyncio
async def test_agent_chat_basic():
    """基础对话测试（不调用工具）"""
    from unittest.mock import AsyncMock, MagicMock, patch

    mock_reply = MagicMock()
    mock_reply.type = "ai"
    mock_reply.content = "你好！我是 Agent，有什么可以帮你？"
    mock_reply.tool_calls = []

    with patch("core.agent.load_shared_tools"), \
         patch("core.agent.load_all_skills"), \
         patch("core.agent.get_tool_registry") as mock_tool_reg, \
         patch("core.agent.get_skill_registry") as mock_skill_reg, \
         patch("core.agent.get_llm_provider") as mock_llm_prov, \
         patch("core.graph.build_graph") as mock_build:

        mock_tool_reg.return_value.get_all_schemas.return_value = []
        mock_skill_reg.return_value.get_all_schemas.return_value = []
        mock_llm_prov.return_value.get_model_with_tools.return_value = MagicMock()

        mock_graph = AsyncMock()
        mock_graph.ainvoke.return_value = {
            "messages": [mock_reply],
            "tools_used": [],
            "retrieved_memory": [],
        }
        mock_build.return_value = mock_graph

        from core.agent import Agent
        agent = Agent()
        result = await agent.chat("你好", session_id="test")

        assert "reply" in result
        assert isinstance(result["tools_used"], list)
        assert isinstance(result["memory_retrieved"], int)


def test_skill_registry():
    from skills.registry import SkillRegistry
    from skills.base import BaseSkill, SkillResult

    class MockSkill(BaseSkill):
        name = "mock"
        description = "测试 Skill"

        async def run(self, **kwargs) -> SkillResult:
            return SkillResult(success=True, data="ok")

    registry = SkillRegistry()
    registry.register(MockSkill)
    assert "mock" in registry.list_skills()
    schemas = registry.get_all_schemas()
    assert any(s["name"] == "mock" for s in schemas)
