"""技术工单自动分派：按技术人员擅长领域进行向量匹配，推荐前 N 名。"""
from stores import get_technician_store


def match_technicians(ticket, k=3):
    query = f"{ticket['title']} {ticket['description'] or ''} {ticket['category'] or ''}"
    hits = get_technician_store().search(query, k=k)
    results = []
    for h in hits:
        results.append({
            "id": int(h["id"]),
            "name": h["metadata"].get("name"),
            "expertise": h["metadata"].get("expertise"),
            "score": round(max(0.0, min(1.0, h["score"] * 1.6)), 3),
        })
    return results


def assign_ticket(ticket_id, technician_id):
    """人工确认后，把工单正式分派给某位技术人员。"""
    from db import get_conn
    conn = get_conn()
    tech = conn.execute("SELECT id, name FROM technicians WHERE id = ?", (technician_id,)).fetchone()
    if not tech:
        conn.close()
        return None
    conn.execute(
        "UPDATE tickets SET assignee_id = ?, assignee_name = ?, status = 'assigned', "
        "updated_at = datetime('now', 'localtime') WHERE id = ?",
        (tech["id"], tech["name"], ticket_id),
    )
    conn.execute("UPDATE technicians SET load_count = load_count + 1 WHERE id = ?", (technician_id,))
    conn.commit()
    conn.close()
    return tech["name"]
