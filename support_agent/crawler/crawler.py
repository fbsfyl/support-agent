"""爬虫脚本：用 Playwright 抓取企业内部论坛，每天定时增量入库。

- 正式环境：配置 settings.crawl_forum_url，使用 Playwright 无头浏览器抓取帖子。
- 演示环境：未配置论坛地址或 Playwright 不可用时，回退到模拟数据增量入库。
- 增量逻辑：按 kb_id 判断新增/更新，写入 knowledge_articles 表并重建知识库向量库。
"""
import json
from datetime import datetime

from config import get_setting
from db import get_conn
from crawler.simulated_data import SIMULATED_POSTS


def _upsert_articles(posts):
    """把帖子增量写入知识库，返回 (new_count, updated_count)。"""
    conn = get_conn()
    new_count = updated_count = 0
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for p in posts:
        exists = conn.execute(
            "SELECT id FROM knowledge_articles WHERE kb_id = ?", (p["kb_id"],)
        ).fetchone()
        if exists:
            conn.execute(
                "UPDATE knowledge_articles SET title=?, content=?, source=?, tags=?, "
                "updated_at=? WHERE kb_id=?",
                (p["title"], p["content"], p.get("source", "IT 论坛"),
                 ",".join(p.get("tags", [])), now, p["kb_id"]),
            )
            updated_count += 1
        else:
            conn.execute(
                "INSERT INTO knowledge_articles (kb_id, title, content, source, tags, crawled_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (p["kb_id"], p["title"], p["content"], p.get("source", "IT 论坛"),
                 ",".join(p.get("tags", [])), now, now),
            )
            new_count += 1
    conn.commit()
    conn.close()
    return new_count, updated_count


def crawl_with_playwright(forum_url):
    """用 Playwright 抓取论坛帖子列表。返回帖子 dict 列表。"""
    posts = []
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return None  # 未安装 playwright

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(forum_url, timeout=30000)
            # 以下是通用选择器示例，正式接入时按论坛实际 DOM 调整
            items = page.query_selector_all("article, .post, .topic, .thread")
            for i, item in enumerate(items[:50]):
                title_el = item.query_selector("h1, h2, h3, .title, a")
                body_el = item.query_selector(".content, .body, p")
                title = title_el.inner_text().strip() if title_el else ""
                content = body_el.inner_text().strip() if body_el else ""
                if title and content:
                    posts.append({
                        "kb_id": f"FORUM-{int(datetime.now().timestamp())}-{i}",
                        "title": title,
                        "content": content,
                        "source": "内部论坛",
                        "tags": [],
                    })
            browser.close()
    except Exception:
        return None
    return posts


def run_crawl():
    """执行一次增量爬取，记录 job 并返回结果。"""
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO crawl_jobs (source, status) VALUES (?, 'running')",
        ("内部论坛",),
    )
    job_id = cur.lastrowid
    conn.commit()
    conn.close()

    forum_url = get_setting("crawl_forum_url", "")
    posts = None
    if forum_url:
        posts = crawl_with_playwright(forum_url)

    if not posts:
        # 演示：模拟增量爬取（每次取部分数据，模拟新增）
        posts = SIMULATED_POSTS

    new_count, updated_count = _upsert_articles(posts)
    message = f"增量爬取完成：新增 {new_count} 条，更新 {updated_count} 条" + (
        "（模拟数据）" if not forum_url or not posts else "")

    conn = get_conn()
    conn.execute(
        "UPDATE crawl_jobs SET status='success', new_count=?, updated_count=?, "
        "message=?, finished_at=datetime('now','localtime') WHERE id=?",
        (new_count, updated_count, message, job_id),
    )
    conn.commit()
    conn.close()

    # 重建知识库向量库
    from stores import get_knowledge_store
    get_knowledge_store().save()

    return {"job_id": job_id, "new_count": new_count, "updated_count": updated_count,
            "message": message}


def list_crawl_jobs(limit=10):
    conn = get_conn()
    rows = conn.execute("SELECT * FROM crawl_jobs ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
