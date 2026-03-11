import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from memory.short_term import ShortTermMemory
from langchain_core.messages import HumanMessage, AIMessage


def test_short_term_add_and_get():
    mem = ShortTermMemory()
    sid = "test_session_1"
    mem.clear(sid)

    mem.add("user", "你好", sid)
    mem.add("assistant", "你好，有什么可以帮你？", sid)

    history = mem.get_history(sid)
    assert len(history) == 2
    assert isinstance(history[0], HumanMessage)
    assert isinstance(history[1], AIMessage)
    assert history[0].content == "你好"


def test_short_term_clear():
    mem = ShortTermMemory()
    sid = "test_session_2"
    mem.add("user", "test", sid)
    mem.clear(sid)
    assert mem.get_history(sid) == []


def test_short_term_turn_count():
    mem = ShortTermMemory()
    sid = "test_session_3"
    mem.clear(sid)
    mem.add("user", "q1", sid)
    mem.add("assistant", "a1", sid)
    mem.add("user", "q2", sid)
    mem.add("assistant", "a2", sid)
    assert mem.get_turn_count(sid) == 2


def test_long_term_save_and_search():
    """需要本地运行 Elasticsearch（http://localhost:9200）"""
    pytest.importorskip("elasticsearch")

    from config.settings import get_settings
    get_settings.cache_clear()

    from memory.long_term import LongTermMemory
    try:
        mem = LongTermMemory()
    except Exception:
        pytest.skip("Elasticsearch 未启动，跳过此测试")

    mem.clear_all()
    mem_id = mem.save("Python 是一种高级编程语言", metadata={"tag": "test"})
    assert mem_id != ""

    import time; time.sleep(1)  # 等待 ES refresh
    results = mem.search("编程语言", top_k=1)
    assert len(results) >= 1
    assert "Python" in results[0]["content"]
