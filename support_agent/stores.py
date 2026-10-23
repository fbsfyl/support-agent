"""向量库注册中心：知识库向量库 + 技术人员擅长向量库。

- 知识库向量库：来源是爬虫脚本增量入库的文章（企业内部论坛 / 帮助中心）。
- 技术人员向量库：把每位技术人员的擅长领域预先写入向量库，用于工单自动分派。
"""
from vector_store import VectorStore


def get_knowledge_store():
    from db import get_conn
    store = VectorStore("knowledge")
    store.clear()
    conn = get_conn()
    rows = conn.execute("SELECT id, kb_id, title, content, tags FROM knowledge_articles").fetchall()
    conn.close()
    for r in rows:
        text = f"{r['title']} {r['content']} {' '.join((r['tags'] or '').split(','))}"
        store.add(r["id"], text, {
            "kb_id": r["kb_id"], "title": r["title"], "tags": r["tags"],
        })
    return store


def get_technician_store():
    from db import get_conn
    store = VectorStore("technicians")
    store.clear()
    conn = get_conn()
    rows = conn.execute("SELECT id, name, expertise, skill_tags FROM technicians WHERE is_active = 1").fetchall()
    conn.close()
    for r in rows:
        text = f"{r['name']} 擅长 {r['expertise']} {' '.join((r['skill_tags'] or '').split(','))}"
        store.add(r["id"], text, {"name": r["name"], "expertise": r["expertise"]})
    return store


def rebuild_and_save():
    ks = get_knowledge_store()
    ts = get_technician_store()
    ks.save()
    ts.save()
    return ks, ts
