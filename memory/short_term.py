import json
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

from config.settings import get_settings
from utils.logger import logger


class ShortTermMemory:
    """
    短期记忆：基于 Redis 的会话对话历史。
    - 按 session_id 隔离
    - TTL 自动过期（默认 1 小时）
    - 最大保留 N 轮对话（超出后自动裁剪）
    """

    def __init__(self):
        self.settings = get_settings()
        self.max_turns = self.settings.short_term_max_turns
        self._init_redis()

    def _init_redis(self):
        import redis
        self._redis = redis.from_url(
            self.settings.redis_url,
            decode_responses=True,
        )
        self._ttl = self.settings.redis_ttl
        # 连通性检查
        self._redis.ping()
        logger.info(f"短期记忆 Redis 已连接: {self.settings.redis_url}")

    def _key(self, session_id: str) -> str:
        return f"stm:{session_id}"

    # ── 写入 ──────────────────────────────────────────────────────

    def add(self, role: str, content: str, session_id: str) -> None:
        """追加一条消息，超出 max_turns 时自动裁剪旧消息"""
        key = self._key(session_id)
        entry = json.dumps({"role": role, "content": content}, ensure_ascii=False)
        pipe = self._redis.pipeline()
        pipe.rpush(key, entry)
        # 超出窗口则从左侧裁剪（保留最新 max_turns * 2 条）
        pipe.ltrim(key, -(self.max_turns * 2), -1)
        pipe.expire(key, self._ttl)
        pipe.execute()

    # ── 读取 ──────────────────────────────────────────────────────

    def get_history(self, session_id: str) -> list[BaseMessage]:
        raw_list = self._redis.lrange(self._key(session_id), 0, -1)
        messages = []
        for raw in raw_list:
            item = json.loads(raw)
            role, content = item["role"], item["content"]
            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))
            elif role == "system":
                messages.append(SystemMessage(content=content))
        return messages

    def get_raw_history(self, session_id: str) -> list[dict]:
        """返回原始 dict 列表，供调试或 API 查看"""
        return [json.loads(r) for r in self._redis.lrange(self._key(session_id), 0, -1)]

    # ── 管理 ──────────────────────────────────────────────────────

    def clear(self, session_id: str) -> None:
        self._redis.delete(self._key(session_id))
        logger.debug(f"短期记忆已清除: session_id={session_id}")

    def get_turn_count(self, session_id: str) -> int:
        length = self._redis.llen(self._key(session_id))
        return length // 2

    def refresh_ttl(self, session_id: str) -> None:
        """重置 TTL，用于活跃会话保活"""
        self._redis.expire(self._key(session_id), self._ttl)
