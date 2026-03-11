import json
from typing import Literal
from langchain_core.messages import SystemMessage, ToolMessage, AIMessage

from langgraph.graph import StateGraph, END

from core.state import AgentState
from memory.short_term import ShortTermMemory
from memory.long_term import LongTermMemory
from tools.registry import get_tool_registry
from skills.registry import get_skill_registry
from utils.logger import logger


SYSTEM_PROMPT = """你是一个通用 AI 助手，具备以下能力：
- 调用工具（web_search、file_read、file_write）获取信息或操作文件
- 调用 Skill（research、summarize、data_analysis、write_report）完成复杂任务
- 调用教育技能（edu__ 开头）完成教学设计任务，涵盖课程规划、评估设计、间隔练习、脚手架搭建等 14 个教育领域
- 利用长期记忆中的历史知识辅助回答

教育技能使用说明：
- 名称格式：edu__<domain>__<skill-name>，如 edu__memory-learning-science__spaced-practice-scheduler
- 每个技能标注了 evidence_strength（strong/moderate/emerging），优先推荐 strong 级别
- 技能返回结果中包含 chains_well_with 字段，提示可继续链式调用的后续技能

请根据用户需求选择合适的工具或 Skill。如果不需要工具，直接回答即可。"""


def build_graph(llm_with_tools):
    """
    构建 LangGraph 推理图。
    节点：memory_retrieve → llm_call → tool_executor（条件） → END
    """
    short_mem = ShortTermMemory()
    long_mem = LongTermMemory()
    tool_registry = get_tool_registry()
    skill_registry = get_skill_registry()

    # ── 节点定义 ──────────────────────────────────────────────────

    def memory_retrieve_node(state: AgentState) -> dict:
        """从长期记忆检索相关信息，注入到 messages 上下文"""
        if not state.messages:
            return {}
        last_user_msg = next(
            (m.content for m in reversed(state.messages) if hasattr(m, "type") and m.type == "human"),
            ""
        )
        if not last_user_msg:
            return {}

        memories = long_mem.search(last_user_msg, top_k=3)
        if not memories:
            return {"retrieved_memory": []}

        memory_text = "\n".join(
            f"- [{i+1}] {m['content'][:200]}" for i, m in enumerate(memories)
        )
        system_with_memory = SystemMessage(
            content=f"{SYSTEM_PROMPT}\n\n【相关历史记忆】\n{memory_text}"
        )
        logger.debug(f"长期记忆检索到 {len(memories)} 条")
        return {
            "retrieved_memory": memories,
            "messages": [system_with_memory],
        }

    def llm_call_node(state: AgentState) -> dict:
        """调用 LLM，决定直接回答还是调用工具/Skill"""
        # 确保有 system prompt
        has_system = any(isinstance(m, SystemMessage) for m in state.messages)
        messages = state.messages
        if not has_system:
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(messages)

        response: AIMessage = llm_with_tools.invoke(messages)
        logger.debug(f"LLM 响应: tool_calls={len(response.tool_calls) if response.tool_calls else 0}")
        return {"messages": [response]}

    async def tool_executor_node(state: AgentState) -> dict:
        """执行 LLM 要求的工具或 Skill 调用"""
        last_message = state.messages[-1]
        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return {}

        tool_messages = []
        tools_used = list(state.tools_used)

        for tc in last_message.tool_calls:
            name = tc["name"]
            args = tc["args"]
            call_id = tc["id"]
            tools_used.append(name)

            # 优先查 Skill，再查 Tool
            skill = skill_registry.get(name)
            if skill:
                result = await skill_registry.execute(name, **args)
                content = json.dumps(result.data, ensure_ascii=False) if result.success else result.error
            else:
                result = tool_registry.execute(name, **args)
                content = str(result.data) if result.success else result.error

            tool_messages.append(
                ToolMessage(content=content, tool_call_id=call_id)
            )
            logger.info(f"执行完成: {name} → {'成功' if result.success else '失败'}")

        return {"messages": tool_messages, "tools_used": tools_used}

    def should_continue(state: AgentState) -> Literal["tool_executor", "end"]:
        """路由：有工具调用 → tool_executor，否则 → end"""
        last = state.messages[-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tool_executor"
        return "end"

    # ── 构建图 ────────────────────────────────────────────────────

    graph = StateGraph(AgentState)
    graph.add_node("memory_retrieve", memory_retrieve_node)
    graph.add_node("llm_call", llm_call_node)
    graph.add_node("tool_executor", tool_executor_node)

    graph.set_entry_point("memory_retrieve")
    graph.add_edge("memory_retrieve", "llm_call")
    graph.add_conditional_edges(
        "llm_call",
        should_continue,
        {"tool_executor": "tool_executor", "end": END},
    )
    graph.add_edge("tool_executor", "llm_call")  # 工具执行后回到 LLM 继续推理

    return graph.compile()
