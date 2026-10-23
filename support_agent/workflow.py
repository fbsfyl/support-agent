"""产品工作流编排：四节点 + 人工评估把关。

四个节点（与前端流程可视化一致）：
  1) 工单接入 intake
  2) 智能分类 classified
  3) 自动处理/分派 processing（技术->推荐技术人员；产品->Agent 自动回复）
  4) 解决闭环 resolved

人工评估（review）位于节点 3 与节点 4 之间：
  - 人工「通过」：提交到下一环节（技术->正式分派；产品->发送回复），再进入解决闭环。
  - 人工「驳回」：重新走节点 3（重新分派 / 重新生成回复）。

说明：本模块用清晰的状态机实现工作流；节点 3 的自动回复可无缝切换到
deepagents 框架（见 deepagents_agent.py），未安装时降级为内置 RAG。
"""
import json

from db import get_conn
from llm import classify_ticket
from knowledge import auto_reply_for_ticket
from assignment import match_technicians, assign_ticket
from config import get_setting

# 状态常量
STATUS_INTAKE = "intake"
STATUS_CLASSIFIED = "classified"
STATUS_PROCESSING = "processing"
STATUS_REVIEW = "review"
STATUS_ASSIGNED = "assigned"
STATUS_REPLIED = "replied"
STATUS_RESOLVED = "resolved"
STATUS_REJECTED = "rejected"

STATUS_LABELS = {
    STATUS_INTAKE: "工单接入",
    STATUS_CLASSIFIED: "已分类",
    STATUS_PROCESSING: "处理中",
    STATUS_REVIEW: "待人工评估",
    STATUS_ASSIGNED: "已分派",
    STATUS_REPLIED: "已回复",
    STATUS_RESOLVED: "已解决",
    STATUS_REJECTED: "已驳回",
}


def get_ticket(ticket_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def _log(ticket_id, node, action, detail, operator="system"):
    conn = get_conn()
    conn.execute(
        "INSERT INTO workflow_logs (ticket_id, node, action, detail, operator) "
        "VALUES (?, ?, ?, ?, ?)",
        (ticket_id, node, action, detail, operator),
    )
    conn.commit()
    conn.close()


def _update(ticket_id, **fields):
    if not fields:
        return
    fields["updated_at"] = "datetime('now', 'localtime')"
    sets = ", ".join(f"{k} = ?" for k in fields)
    conn = get_conn()
    conn.execute(
        f"UPDATE tickets SET {sets} WHERE id = ?",
        list(fields.values()) + [ticket_id],
    )
    conn.commit()
    conn.close()


# ---------------- 节点 1：工单接入 ----------------
def create_ticket(title, description, source="web"):
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO tickets (ticket_no, title, description, source, status) "
        "VALUES (?, ?, ?, ?, ?)",
        ("", title, description, source, STATUS_INTAKE),
    )
    ticket_id = cur.lastrowid
    conn.execute("UPDATE tickets SET ticket_no = ? WHERE id = ?",
                 (f"#TK-2024-{ticket_id:04d}", ticket_id))
    conn.commit()
    conn.close()
    _log(ticket_id, "工单接入", "create", f"新工单接入：{title}", "system")
    return get_ticket(ticket_id)


# ---------------- 节点 2：智能分类 ----------------
def classify(ticket_id):
    t = get_ticket(ticket_id)
    if not t:
        return None
    result = classify_ticket(t["title"], t["description"])
    prefix = "PR" if result["ttype"] == "产品" else "TK"
    _update(
        ticket_id,
        ttype=result["ttype"],
        category=result["category"],
        priority=result["priority"],
        tags=json.dumps(result.get("tags", []), ensure_ascii=False),
        status=STATUS_CLASSIFIED,
    )
    conn = get_conn()
    conn.execute("UPDATE tickets SET ticket_no = ? WHERE id = ?",
                 (f"#{prefix}-2024-{ticket_id:04d}", ticket_id))
    conn.commit()
    conn.close()
    _log(ticket_id, "智能分类", "classify",
         f"分类：{result['ttype']} / {result['category']} / {result['priority']}", "system")
    return get_ticket(ticket_id)


# ---------------- 节点 3：自动处理/分派 ----------------
def auto_process(ticket_id):
    t = get_ticket(ticket_id)
    if not t:
        return None
    _update(ticket_id, status=STATUS_PROCESSING)

    if t["ttype"] == "技术":
        top_k = int(get_setting("assign_top_k", "3") or 3)
        cands = match_technicians(t, k=top_k)
        _update(ticket_id,
                candidates=json.dumps(cands, ensure_ascii=False),
                match_score=cands[0]["score"] if cands else None,
                status=STATUS_REVIEW)
        _log(ticket_id, "自动处理/分派", "match",
             f"推荐 {len(cands)} 名技术人员：" + "、".join(c["name"] for c in cands[:3]), "agent")
    else:
        reply, confidence, sources, threshold = auto_reply_for_ticket(t)
        _update(ticket_id,
                auto_reply=reply,
                reply_confidence=confidence,
                reply_sources=json.dumps(sources, ensure_ascii=False),
                status=STATUS_REVIEW)
        _log(ticket_id, "自动处理/分派", "auto_reply",
             f"生成自动回复，置信度 {confidence:.0%}（阈值 {threshold:.0%}）", "agent")
    return get_ticket(ticket_id)


# ---------------- 一键处理到待评估 ----------------
def process_ticket(ticket_id):
    t = get_ticket(ticket_id)
    if not t:
        return None
    if t["status"] in (STATUS_INTAKE, STATUS_REJECTED):
        classify(ticket_id)
    auto_process(ticket_id)
    return get_ticket(ticket_id)


# ---------------- 人工评估：通过 / 驳回 ----------------
def human_approve(ticket_id, assignee_id=None):
    t = get_ticket(ticket_id)
    if not t:
        return None
    if t["ttype"] == "技术":
        if assignee_id is None:
            cands = json.loads(t["candidates"] or "[]")
            assignee_id = cands[0]["id"] if cands else None
        if assignee_id:
            name = assign_ticket(ticket_id, int(assignee_id))
            _log(ticket_id, "人工评估", "approve", f"评估通过，正式分派给 {name}", "human")
        else:
            _update(ticket_id, status=STATUS_REVIEW)
    else:
        _update(ticket_id, status=STATUS_REPLIED)
        _log(ticket_id, "人工评估", "approve", "评估通过，确认发送自动回复", "human")
    return get_ticket(ticket_id)


def human_reject(ticket_id, reason=""):
    t = get_ticket(ticket_id)
    if not t:
        return None
    _update(ticket_id, status=STATUS_REJECTED, reject_reason=reason)
    _log(ticket_id, "人工评估", "reject", f"评估驳回：{reason or '未填写原因'}，重新走流程", "human")
    # 重新执行节点 3（重新分派 / 重新生成回复）
    auto_process(ticket_id)
    return get_ticket(ticket_id)


def escalate_ticket(ticket_id, reason=""):
    """已发送/已分派的工单转人工：用户要求人工介入时，打回待人工评估。"""
    t = get_ticket(ticket_id)
    if not t:
        return None
    if t["status"] not in (STATUS_REPLIED, STATUS_ASSIGNED):
        return t
    _update(ticket_id, status=STATUS_REVIEW, reject_reason=reason)
    _log(ticket_id, "人工评估", "escalate",
         f"用户要求人工介入，转回人工评估：{reason or '未填写原因'}", "human")
    return get_ticket(ticket_id)


# ---------------- 节点 4：解决闭环 ----------------
def resolve_ticket(ticket_id):
    t = get_ticket(ticket_id)
    if not t:
        return None
    _update(ticket_id, status=STATUS_RESOLVED)
    _log(ticket_id, "解决闭环", "resolve", "工单关闭，进入满意度回访", "human")
    return get_ticket(ticket_id)


def get_logs(ticket_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM workflow_logs WHERE ticket_id = ? ORDER BY id ASC", (ticket_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
