from fastapi import APIRouter
from memory.short_term import ShortTermMemory
from memory.long_term import LongTermMemory
from tools.registry import get_tool_registry
from skills.registry import get_skill_registry

router = APIRouter()
_short_mem = ShortTermMemory()
_long_mem = LongTermMemory()


@router.get("/memory/{session_id}")
def get_session_memory(session_id: str):
    history = _short_mem.get_history(session_id)
    return {
        "session_id": session_id,
        "turn_count": _short_mem.get_turn_count(session_id),
        "history": [{"type": m.type, "content": m.content} for m in history],
    }


@router.delete("/memory/{session_id}")
def clear_session_memory(session_id: str):
    _short_mem.clear(session_id)
    return {"message": f"会话 {session_id} 记忆已清除"}


@router.get("/tools")
def list_tools():
    tools = get_tool_registry().get_all_schemas()
    skills = get_skill_registry().get_all_schemas()
    return {
        "tools": tools,
        "skills": skills,
        "total": len(tools) + len(skills),
    }


@router.get("/memory/long-term/stats")
def long_term_stats():
    return {"total_entries": _long_mem.count()}
