"""Flask 后端：智能工单系统 API + 页面渲染。"""
import json
from datetime import datetime

from flask import Flask, jsonify, render_template, request

from config import get_all_settings, set_settings, init_settings
from db import init_db, get_conn
import workflow as wf
from assignment import match_technicians
from crawler.crawler import run_crawl, list_crawl_jobs
from stores import get_knowledge_store, get_technician_store

app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False


# ---------------- 工具函数 ----------------
def _ticket_dict(row):
    d = dict(row)
    d["tags"] = json.loads(d.get("tags") or "[]") if isinstance(d.get("tags"), str) else (d.get("tags") or [])
    d["candidates"] = json.loads(d.get("candidates") or "[]") if isinstance(d.get("candidates"), str) else (d.get("candidates") or [])
    d["reply_sources"] = json.loads(d.get("reply_sources") or "[]") if isinstance(d.get("reply_sources"), str) else (d.get("reply_sources") or [])
    d["status_label"] = wf.STATUS_LABELS.get(d.get("status"), d.get("status"))
    return d


def _kpi():
    conn = get_conn()
    today = datetime.now().strftime("%Y-%m-%d")
    today_count = conn.execute(
        "SELECT COUNT(*) c FROM tickets WHERE date(created_at) = ?", (today,)
    ).fetchone()["c"]
    total = conn.execute("SELECT COUNT(*) c FROM tickets").fetchone()["c"]
    product_total = conn.execute("SELECT COUNT(*) c FROM tickets WHERE ttype='产品'").fetchone()["c"] or 0
    product_auto = conn.execute(
        "SELECT COUNT(*) c FROM tickets WHERE ttype='产品' AND status IN ('replied','resolved')"
    ).fetchone()["c"] or 0
    pending = conn.execute(
        "SELECT COUNT(*) c FROM tickets WHERE ttype='技术' AND status='review'"
    ).fetchone()["c"]
    resolved = conn.execute("SELECT COUNT(*) c FROM tickets WHERE status='resolved'").fetchone()["c"]
    conn.close()

    auto_rate = round(product_auto / product_total * 100, 1) if product_total else 0
    return {
        "today_count": today_count,
        "total_count": total,
        "auto_rate": auto_rate,
        "pending": pending,
        "resolved": resolved,
        "avg_response_min": 2.3,
    }


def _flow_counts():
    conn = get_conn()
    def c(cond):
        return conn.execute(f"SELECT COUNT(*) c FROM tickets WHERE {cond}").fetchone()["c"]
    result = {
        "intake": c("status='intake'"),
        "classified": c("status='classified'"),
        "processing": c("status IN ('processing','review','rejected')"),
        "resolved": c("status IN ('assigned','replied','resolved')"),
    }
    conn.close()
    return result


# ---------------- 页面 ----------------
@app.route("/")
def index():
    return render_template("index.html")


# ---------------- 看板 ----------------
@app.route("/api/dashboard")
def dashboard():
    conn = get_conn()
    kpi = _kpi()
    flow = _flow_counts()

    pending_rows = conn.execute(
        "SELECT * FROM tickets WHERE ttype='技术' AND status='review' ORDER BY priority, id DESC LIMIT 6"
    ).fetchall()
    pending = [_ticket_dict(r) for r in pending_rows]

    agent_rows = conn.execute(
        "SELECT * FROM tickets WHERE ttype='产品' AND status IN ('processing','review') "
        "ORDER BY id DESC LIMIT 6"
    ).fetchall()
    agent = [_ticket_dict(r) for r in agent_rows]

    recent_rows = conn.execute(
        "SELECT * FROM tickets ORDER BY id DESC LIMIT 5"
    ).fetchall()
    recent = [_ticket_dict(r) for r in recent_rows]
    conn.close()

    return jsonify({"kpi": kpi, "flow": flow, "pending": pending, "agent": agent, "recent": recent})


# ---------------- 工单 ----------------
@app.route("/api/tickets")
def list_tickets():
    status = request.args.get("status")
    ttype = request.args.get("ttype")
    search = request.args.get("search")
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 20))

    where, params = [], []
    if status:
        where.append("status = ?"); params.append(status)
    if ttype:
        where.append("ttype = ?"); params.append(ttype)
    if search:
        where.append("(title LIKE ? OR description LIKE ? OR ticket_no LIKE ?)")
        params += [f"%{search}%"] * 3
    cond = ("WHERE " + " AND ".join(where)) if where else ""

    conn = get_conn()
    total = conn.execute(f"SELECT COUNT(*) c FROM tickets {cond}", params).fetchone()["c"]
    rows = conn.execute(
        f"SELECT * FROM tickets {cond} ORDER BY id DESC LIMIT ? OFFSET ?",
        params + [per_page, (page - 1) * per_page],
    ).fetchall()
    conn.close()
    return jsonify({"total": total, "items": [_ticket_dict(r) for r in rows]})


@app.route("/api/tickets", methods=["POST"])
def create_ticket():
    data = request.get_json(force=True)
    t = wf.create_ticket(data.get("title", ""), data.get("description", ""), data.get("source", "web"))
    return jsonify({"ok": True, "ticket": _ticket_dict(t)})


@app.route("/api/tickets/<int:tid>")
def ticket_detail(tid):
    conn = get_conn()
    row = conn.execute("SELECT * FROM tickets WHERE id = ?", (tid,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"ok": False, "error": "not found"}), 404
    return jsonify({"ok": True, "ticket": _ticket_dict(row), "logs": wf.get_logs(tid)})


@app.route("/api/tickets/<int:tid>/process", methods=["POST"])
def process_ticket(tid):
    t = wf.process_ticket(tid)
    return jsonify({"ok": True, "ticket": _ticket_dict(t) if t else None})


@app.route("/api/tickets/<int:tid>/approve", methods=["POST"])
def approve_ticket(tid):
    data = request.get_json(silent=True) or {}
    t = wf.human_approve(tid, data.get("assignee_id"))
    return jsonify({"ok": True, "ticket": _ticket_dict(t) if t else None})


@app.route("/api/tickets/<int:tid>/reject", methods=["POST"])
def reject_ticket(tid):
    data = request.get_json(silent=True) or {}
    t = wf.human_reject(tid, data.get("reason", ""))
    return jsonify({"ok": True, "ticket": _ticket_dict(t) if t else None})


@app.route("/api/tickets/<int:tid>/assign", methods=["POST"])
def assign_ticket_api(tid):
    data = request.get_json(force=True)
    t = wf.human_approve(tid, data.get("assignee_id"))
    return jsonify({"ok": True, "ticket": _ticket_dict(t) if t else None})


@app.route("/api/tickets/<int:tid>/resolve", methods=["POST"])
def resolve_ticket_api(tid):
    t = wf.resolve_ticket(tid)
    return jsonify({"ok": True, "ticket": _ticket_dict(t) if t else None})


@app.route("/api/tickets/<int:tid>/escalate", methods=["POST"])
def escalate_ticket_api(tid):
    data = request.get_json(silent=True) or {}
    t = wf.escalate_ticket(tid, data.get("reason", ""))
    return jsonify({"ok": True, "ticket": _ticket_dict(t) if t else None})


@app.route("/api/tickets/<int:tid>/reply", methods=["PUT"])
def edit_reply_api(tid):
    data = request.get_json(force=True)
    conn = get_conn()
    conn.execute(
        "UPDATE tickets SET auto_reply = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
        (data.get("auto_reply", ""), tid),
    )
    conn.commit()
    conn.close()
    return jsonify({"ok": True})


# ---------------- 技术人员 ----------------
@app.route("/api/technicians")
def list_technicians():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM technicians ORDER BY id").fetchall()
    conn.close()
    return jsonify({"items": [dict(r) for r in rows]})


@app.route("/api/technicians", methods=["POST"])
def add_technician():
    data = request.get_json(force=True)
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO technicians (name, title, expertise, skill_tags) VALUES (?, ?, ?, ?)",
        (data.get("name"), data.get("title", ""), data.get("expertise", ""), data.get("skill_tags", "")),
    )
    conn.commit()
    conn.close()
    get_technician_store().save()
    return jsonify({"ok": True, "id": cur.lastrowid})


@app.route("/api/technicians/<int:uid>", methods=["PUT"])
def update_technician(uid):
    data = request.get_json(force=True)
    conn = get_conn()
    conn.execute(
        "UPDATE technicians SET name=?, title=?, expertise=?, skill_tags=?, is_active=? WHERE id=?",
        (data.get("name"), data.get("title", ""), data.get("expertise", ""),
         data.get("skill_tags", ""), 1 if data.get("is_active", True) else 0, uid),
    )
    conn.commit()
    conn.close()
    get_technician_store().save()
    return jsonify({"ok": True})


@app.route("/api/technicians/<int:uid>", methods=["DELETE"])
def delete_technician(uid):
    conn = get_conn()
    conn.execute("DELETE FROM technicians WHERE id=?", (uid,))
    conn.commit()
    conn.close()
    get_technician_store().save()
    return jsonify({"ok": True})


# ---------------- 知识库 ----------------
@app.route("/api/knowledge")
def list_knowledge():
    search = request.args.get("search")
    conn = get_conn()
    if search:
        rows = conn.execute(
            "SELECT * FROM knowledge_articles WHERE title LIKE ? OR content LIKE ? ORDER BY id DESC",
            (f"%{search}%", f"%{search}%"),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM knowledge_articles ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify({"items": [dict(r) for r in rows]})


@app.route("/api/knowledge/search")
def search_knowledge():
    q = request.args.get("q", "")
    store = get_knowledge_store()
    hits = store.search(q, k=5)
    return jsonify({"dim": store.dim, "count": len(store.ids),
                    "items": hits})


@app.route("/api/knowledge", methods=["POST"])
def add_knowledge():
    data = request.get_json(force=True)
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO knowledge_articles (kb_id, title, content, source, tags) VALUES (?, ?, ?, ?, ?)",
        (data.get("kb_id"), data.get("title"), data.get("content"),
         data.get("source", "手工"), data.get("tags", "")),
    )
    conn.commit()
    conn.close()
    get_knowledge_store().save()
    return jsonify({"ok": True, "id": cur.lastrowid})


# ---------------- 设置 ----------------
@app.route("/api/settings")
def get_settings():
    return jsonify(get_all_settings())


@app.route("/api/settings", methods=["PUT"])
def update_settings():
    data = request.get_json(force=True)
    set_settings(data)
    return jsonify({"ok": True})


# ---------------- 爬虫 ----------------
@app.route("/api/crawl/run", methods=["POST"])
def crawl_now():
    try:
        result = run_crawl()
        return jsonify({"ok": True, **result})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/crawl/jobs")
def crawl_jobs():
    return jsonify({"items": list_crawl_jobs(10)})


# ---------------- 数据分析 ----------------
@app.route("/api/analytics")
def analytics():
    conn = get_conn()
    by_type = [dict(r) for r in conn.execute(
        "SELECT ttype, COUNT(*) c FROM tickets GROUP BY ttype").fetchall()]
    by_status = [dict(r) for r in conn.execute(
        "SELECT status, COUNT(*) c FROM tickets GROUP BY status").fetchall()]
    by_tech = [dict(r) for r in conn.execute(
        "SELECT assignee_name, COUNT(*) c FROM tickets WHERE assignee_name IS NOT NULL "
        "GROUP BY assignee_name ORDER BY c DESC").fetchall()]
    conn.close()
    status_map = wf.STATUS_LABELS
    for r in by_status:
        r["label"] = status_map.get(r["status"], r["status"])
    return jsonify({"by_type": by_type, "by_status": by_status, "by_tech": by_tech})


def ensure_initialized():
    init_db()
    init_settings()
    # 若数据库为空，自动执行种子
    conn = get_conn()
    cnt = conn.execute("SELECT COUNT(*) c FROM tickets").fetchone()["c"]
    conn.close()
    if cnt == 0:
        import seed
        seed.seed_all()


ensure_initialized()

# 启动每日定时增量爬取调度器（守护线程）
from scheduler import start_scheduler
start_scheduler()

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", "5000"))
    # 一键启动脚本默认关闭 debug 重载器，便于 stop 脚本干净地按端口停止；
    # 本地调试时可设置 FLASK_DEBUG=1 开启热重载。
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=debug)
