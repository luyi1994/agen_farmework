import uuid
import json
from datetime import datetime
from typing import Optional

from config.settings import get_settings
from utils.logger import logger


class LongTermMemory:
    """
    长期记忆：基于 Elasticsearch 的向量存储，支持跨会话语义检索。
    使用 sentence-transformers 生成 Embedding，ES 的 dense_vector 做 kNN 检索。
    """

    def __init__(self):
        self.settings = get_settings()
        if not self.settings.long_term_enabled:
            logger.info("长期记忆已禁用")
            self._enabled = False
            return
        self._enabled = True
        self._embedding_model = None
        self._init_es()
        self._ensure_index()

    # ── 初始化 ────────────────────────────────────────────────────

    def _init_es(self):
        from elasticsearch import Elasticsearch
        self._es = Elasticsearch(
            self.settings.es_url,
            basic_auth=(self.settings.es_username, self.settings.es_password)
            if self.settings.es_username else None,
            verify_certs=self.settings.es_verify_certs,
        )
        self._index = self.settings.es_index
        info = self._es.info()
        logger.info(f"Elasticsearch 已连接: {self.settings.es_url}, version={info['version']['number']}")

    def _ensure_index(self):
        """创建索引（如不存在），配置 dense_vector 字段支持 kNN"""
        if self._es.indices.exists(index=self._index):
            return
        dim = self._get_embedding_dim()
        mapping = {
            "mappings": {
                "properties": {
                    "content":    {"type": "text",         "analyzer": "standard"},
                    "embedding":  {"type": "dense_vector", "dims": dim, "index": True, "similarity": "cosine"},
                    "metadata":   {"type": "object",       "dynamic": True},
                    "created_at": {"type": "date"},
                }
            }
        }
        self._es.indices.create(index=self._index, body=mapping)
        logger.info(f"ES 索引已创建: {self._index} (dims={dim})")

    def _get_embedding_dim(self) -> int:
        model = self._get_embedding_model()
        sample = model.encode("test")
        return len(sample)

    def _get_embedding_model(self):
        if self._embedding_model is None:
            from sentence_transformers import SentenceTransformer
            self._embedding_model = SentenceTransformer(self.settings.embedding_model)
            logger.debug(f"Embedding 模型已加载: {self.settings.embedding_model}")
        return self._embedding_model

    def _embed(self, text: str) -> list[float]:
        return self._get_embedding_model().encode(text).tolist()

    # ── 写入 ──────────────────────────────────────────────────────

    def save(self, text: str, metadata: Optional[dict] = None) -> str:
        if not self._enabled:
            return ""
        memory_id = str(uuid.uuid4())
        doc = {
            "content":    text,
            "embedding":  self._embed(text),
            "metadata":   metadata or {},
            "created_at": datetime.now().isoformat(),
        }
        self._es.index(index=self._index, id=memory_id, document=doc, refresh="wait_for")
        logger.debug(f"长期记忆已存储: id={memory_id[:8]}...")
        return memory_id

    # ── 检索 ──────────────────────────────────────────────────────

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        if not self._enabled:
            return []
        query_vec = self._embed(query)
        resp = self._es.search(
            index=self._index,
            body={
                "knn": {
                    "field":          "embedding",
                    "query_vector":   query_vec,
                    "k":              top_k,
                    "num_candidates": top_k * 5,
                },
                "_source": ["content", "metadata", "created_at"],
                "size": top_k,
            },
        )
        results = []
        for hit in resp["hits"]["hits"]:
            results.append({
                "content":  hit["_source"]["content"],
                "metadata": hit["_source"].get("metadata", {}),
                "score":    round(hit["_score"], 4),
                "id":       hit["_id"],
            })
        return results

    # ── 管理 ──────────────────────────────────────────────────────

    def delete(self, memory_id: str) -> None:
        if not self._enabled:
            return
        self._es.delete(index=self._index, id=memory_id, ignore=[404])
        logger.debug(f"长期记忆已删除: id={memory_id}")

    def clear_all(self) -> None:
        if not self._enabled:
            return
        self._es.delete_by_query(
            index=self._index,
            body={"query": {"match_all": {}}},
            refresh=True,
        )
        logger.warning("长期记忆已全部清空")

    def count(self) -> int:
        if not self._enabled:
            return 0
        resp = self._es.count(index=self._index)
        return resp["count"]
