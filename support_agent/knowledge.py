"""知识库检索增强生成（RAG）：Agent 自动处理中心的自动回复。"""
from config import get_setting
from llm import generate_reply
from stores import get_knowledge_store


def retrieve(query, k=3):
    store = get_knowledge_store()
    hits = store.search(query, k=k)
    return hits


def score_to_confidence(top_score):
    """把余弦相似度映射到 0~1 的置信度（本地哈希向量的分数偏低，做线性放大）。"""
    return max(0.0, min(1.0, top_score * 1.6))


def auto_reply_for_ticket(ticket):
    """根据工单内容检索知识库并生成自动回复。

    返回 (reply, confidence, sources)。
    """
    query = f"{ticket['title']} {ticket['description'] or ''}"
    hits = retrieve(query, k=3)
    threshold = float(get_setting("auto_reply_confidence_threshold", "0.7") or 0.7)

    # 过滤低相关结果
    good_hits = [h for h in hits if h["score"] > 0.15]
    if not good_hits:
        good_hits = hits[:1] if hits else []

    contexts = [h["metadata"].get("title", "") + "：" + _content_of(h["id"]) for h in good_hits]

    # 优先使用 deepagents 框架的自动回复 Agent（可选），失败则用内置 RAG
    reply = None
    try:
        from deepagents_agent import run_auto_reply_agent
        reply = run_auto_reply_agent(query)
    except Exception:
        reply = None
    if not reply:
        reply = generate_reply(query, contexts)

    top_score = good_hits[0]["score"] if good_hits else 0.0
    confidence = score_to_confidence(top_score)

    sources = [{"kb_id": h["metadata"].get("kb_id"), "title": h["metadata"].get("title"),
                "score": round(h["score"], 3)} for h in good_hits]

    return reply, confidence, sources, threshold


def _content_of(doc_id):
    from db import get_conn
    conn = get_conn()
    row = conn.execute("SELECT content FROM knowledge_articles WHERE id = ?", (doc_id,)).fetchone()
    conn.close()
    return row["content"] if row else ""
