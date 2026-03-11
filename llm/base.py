from abc import ABC, abstractmethod
from typing import Iterator
from langchain_core.language_models import BaseChatModel


class LLMProvider(ABC):
    @abstractmethod
    def get_model(self) -> BaseChatModel:
        """返回标准 BaseChatModel 实例，LangGraph 原生兼容"""

    @abstractmethod
    def get_model_with_tools(self, tools: list) -> BaseChatModel:
        """返回绑定工具 Schema 的模型实例"""
