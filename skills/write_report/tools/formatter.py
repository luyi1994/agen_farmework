from tools.base import tool
from datetime import datetime


@tool(name="markdown_formatter", description="将文本内容格式化为标准 Markdown 报告结构")
def markdown_formatter(title: str, content: str, author: str = "Agent") -> str:
    """生成带标题、日期、作者的 Markdown 格式报告"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    return (
        f"# {title}\n\n"
        f"> 作者：{author} | 生成日期：{date_str}\n\n"
        f"---\n\n"
        f"{content}\n\n"
        f"---\n\n"
        f"*本报告由 Agent 自动生成*"
    )
