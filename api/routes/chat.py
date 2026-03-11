from fastapi import APIRouter
from pydantic import BaseModel, Field
from core.agent import Agent

router = APIRouter()
_agent: Agent | None = None


def get_agent() -> Agent:
    global _agent
    if _agent is None:
        _agent = Agent()
    return _agent


class ChatRequest(BaseModel):
    session_id: str = Field(default="default", description="会话 ID")
    message: str = Field(..., description="用户消息")


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    tools_used: list[str]
    memory_retrieved: int


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    agent = get_agent()
    result = await agent.chat(req.message, req.session_id)
    return ChatResponse(
        session_id=req.session_id,
        reply=result["reply"],
        tools_used=result["tools_used"],
        memory_retrieved=result["memory_retrieved"],
    )
