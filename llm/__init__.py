from .litellm_provider import LiteLLMProvider

def get_llm_provider() -> LiteLLMProvider:
    return LiteLLMProvider()

__all__ = ["LiteLLMProvider", "get_llm_provider"]
