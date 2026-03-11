from tools.base import tool


@tool(name="text_chunker", description="将长文本按段落分块，返回分块列表（JSON 字符串）")
def text_chunker(text: str, chunk_size: int = 1000) -> str:
    """将 text 按 chunk_size 字符分段，返回 JSON 列表"""
    import json

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks, current = [], ""
    for para in paragraphs:
        if len(current) + len(para) > chunk_size and current:
            chunks.append(current.strip())
            current = para
        else:
            current += "\n\n" + para
    if current.strip():
        chunks.append(current.strip())
    return json.dumps(chunks, ensure_ascii=False)
