from tools.base import tool


@tool(name="content_extractor", description="从 URL 中提取网页正文内容")
def content_extractor(url: str) -> str:
    """抓取指定 URL 并提取纯文本正文"""
    import requests
    from bs4 import BeautifulSoup

    headers = {"User-Agent": "Mozilla/5.0 (compatible; AgentBot/1.0)"}
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    lines = [l for l in text.splitlines() if len(l.strip()) > 30]
    return "\n".join(lines[:200])  # 限制 200 行
