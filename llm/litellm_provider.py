import os
from langchain_community.chat_models import ChatLiteLLM
from langchain_core.language_models import BaseChatModel

from .base import LLMProvider
from config.settings import get_settings
from utils.logger import logger


class LiteLLMProvider(LLMProvider):
    """
    基于 LiteLLM 的统一 LLM 接口。
    切换模型只需修改 .env 中的 LLM_MODEL，代码零改动。

    支持：
      - claude-sonnet-4-6       (Anthropic)
      - gpt-4o                  (OpenAI)
      - gemini/gemini-1.5-pro   (Google)
      - ollama/llama3.1         (本地 Ollama)
    """

    def __init__(self):
        self.settings = get_settings()
        self._set_api_keys()
        logger.info(f"LLM Provider 初始化: model={self.settings.llm_model}")

    def _set_api_keys(self):
        if self.settings.anthropic_api_key:
            os.environ["ANTHROPIC_API_KEY"] = self.settings.anthropic_api_key
        if self.settings.openai_api_key:
            os.environ["OPENAI_API_KEY"] = self.settings.openai_api_key
        if self.settings.gemini_api_key:
            os.environ["GEMINI_API_KEY"] = self.settings.gemini_api_key
        if self.settings.llm_base_url:
            os.environ["OPENAI_API_BASE"] = self.settings.llm_base_url

    def get_model(self) -> BaseChatModel:
        kwargs = dict(
            model=self.settings.llm_model,
            temperature=self.settings.llm_temperature,
            max_tokens=self.settings.llm_max_tokens,
        )
        if self.settings.llm_base_url:
            kwargs["api_base"] = self.settings.llm_base_url
        return ChatLiteLLM(**kwargs)

    def get_model_with_tools(self, tools: list) -> BaseChatModel:
        return self.get_model().bind_tools(tools)
