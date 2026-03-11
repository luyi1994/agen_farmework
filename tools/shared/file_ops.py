import os
from tools.base import tool


@tool(name="file_read", description="读取本地文件内容，path 为文件路径")
def file_read(path: str) -> str:
    """读取指定路径的文件内容"""
    if not os.path.exists(path):
        raise FileNotFoundError(f"文件不存在: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@tool(name="file_write", description="将内容写入本地文件，path 为路径，content 为内容")
def file_write(path: str, content: str) -> str:
    """将 content 写入指定 path 文件"""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return f"已写入文件: {path}（{len(content)} 字符）"
