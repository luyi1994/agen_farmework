from tools.base import tool, ToolDefinition
from config.settings import get_settings
from utils.logger import logger


@tool(name="web_search", description="搜索互联网获取最新信息，返回相关搜索结果")
def web_search(query: str) -> str:
    """搜索互联网，query 为搜索关键词"""
    settings = get_settings()
    provider = settings.search_provider

    if provider == "tavily":
        return _tavily_search(query, settings.tavily_api_key)
    else:
        return _duckduckgo_search(query)


def _tavily_search(query: str, api_key: str) -> str:
    from tavily import TavilyClient
    client = TavilyClient(api_key=api_key)
    response = client.search(query=query, max_results=5)
    results = response.get("results", [])
    if not results:
        return "未找到相关结果"
    output = []
    for i, r in enumerate(results, 1):
        output.append(f"[{i}] {r.get('title', '')}\n{r.get('url', '')}\n{r.get('content', '')}")
    return "\n\n".join(output)


def _duckduckgo_search(query: str) -> str:
    from duckduckgo_search import DDGS
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=5):
            results.append(f"[{r['title']}]\n{r['href']}\n{r['body']}")
    return "\n\n".join(results) if results else "未找到相关结果"
