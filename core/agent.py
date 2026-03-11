import asyncio
from langchain_core.messages import HumanMessage

from core.graph import build_graph
from core.state import AgentState
from llm import get_llm_provider
from memory.short_term import ShortTermMemory
from memory.long_term import LongTermMemory
from tools import load_shared_tools, get_tool_registry
from skills import load_all_skills, get_skill_registry
from utils.logger import logger


class Agent:
    """
    通用 Agent 主类，组装所有模块。

    使用方式：
        agent = Agent()
        reply = await agent.chat("帮我调研量子计算最新进展", session_id="user_1")
    """

    def __init__(self):
        # 1. 加载公共工具 + 所有 Skill
        load_shared_tools()
        load_all_skills()

        # 2. 合并 Tool + Skill Schema 交给 LLM
        tool_schemas = get_tool_registry().get_all_schemas()
        skill_schemas = get_skill_registry().get_all_schemas()
        all_schemas = tool_schemas + skill_schemas

        # 3. 初始化 LLM（绑定工具）
        llm_provider = get_llm_provider()
        llm_with_tools = llm_provider.get_model_with_tools(all_schemas)

        # 4. 构建 LangGraph
        self._graph = build_graph(llm_with_tools)

        # 5. 记忆
        self._short_mem = ShortTermMemory()
        self._long_mem = LongTermMemory()

        logger.info(
            f"Agent 初始化完成: "
            f"tools={len(tool_schemas)}, skills={len(skill_schemas)}"
        )

    async def chat(self, message: str, session_id: str = "default") -> dict:
        """
        发送一条消息，返回回复结果。

        Returns:
            {
                "reply": str,
                "tools_used": list[str],
                "memory_retrieved": int,
            }
        """
        # 读取短期记忆历史
        history = self._short_mem.get_history(session_id)

        # 构建初始状态
        initial_state = AgentState(
            session_id=session_id,
            messages=history + [HumanMessage(content=message)],
        )

        # 执行 LangGraph
        final_state = await self._graph.ainvoke(initial_state)

        # 提取最终回答
        reply = ""
        for msg in reversed(final_state["messages"]):
            if hasattr(msg, "type") and msg.type == "ai" and msg.content:
                reply = msg.content
                break

        # 写入短期记忆
        self._short_mem.add("user", message, session_id)
        self._short_mem.add("assistant", reply, session_id)

        return {
            "reply": reply,
            "tools_used": final_state.get("tools_used", []),
            "memory_retrieved": len(final_state.get("retrieved_memory", [])),
        }

    def chat_sync(self, message: str, session_id: str = "default") -> dict:
        """同步版本的 chat，供 CLI 使用"""
        return asyncio.run(self.chat(message, session_id))

    def clear_session(self, session_id: str) -> None:
        self._short_mem.clear(session_id)
        logger.info(f"会话已清除: {session_id}")
