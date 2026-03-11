from typing import Annotated, Any
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class AgentState(BaseModel):
    """LangGraph 状态机的状态定义"""

    session_id: str = ""
    messages: Annotated[list[BaseMessage], add_messages] = Field(default_factory=list)

    # 记忆检索结果（推理前注入）
    retrieved_memory: list[dict] = Field(default_factory=list)

    # 工具/Skill 调用结果（中间状态）
    tool_results: list[dict] = Field(default_factory=list)

    # 最终回答
    final_answer: str = ""

    # 本轮实际调用的工具/Skill 名称列表（供 API 返回）
    tools_used: list[str] = Field(default_factory=list)
