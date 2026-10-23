"""初始化数据库 + 种子数据（技术人员、知识库、示例工单）。"""
import json
from datetime import datetime, timedelta

from config import init_settings
from db import init_db, get_conn
from crawler.simulated_data import SIMULATED_POSTS

TECHNICIANS = [
    {"name": "张明远", "title": "云平台工程师", "expertise": "Azure Kubernetes Service、Docker 容器、云原生架构、负载均衡",
     "skill_tags": "AKS,Kubernetes,Docker,Azure"},
    {"name": "李思琪", "title": "协作办公专家", "expertise": "Microsoft 365、Exchange Online、Outlook 邮件、Teams 会议",
     "skill_tags": "M365,Exchange,Outlook,Teams"},
    {"name": "王浩然", "title": "数据分析工程师", "expertise": "Power BI、SQL Server、数据集刷新、DirectQuery",
     "skill_tags": "PowerBI,SQL Server,数据分析"},
    {"name": "陈嘉伟", "title": "网络与安全工程师", "expertise": "网络排查、防火墙、VPN、证书、DNS 安全",
     "skill_tags": "网络,VPN,防火墙,证书"},
    {"name": "刘雨桐", "title": "系统管理工程师", "expertise": "Windows Server、Active Directory 域控、远程桌面许可",
     "skill_tags": "Windows Server,AD,域控"},
    {"name": "赵敏", "title": "协作存储专家", "expertise": "SharePoint Online、OneDrive、文档库版本控制、权限管理",
     "skill_tags": "SharePoint,OneDrive,版本控制"},
]

SAMPLE_TICKETS = [
    {"ttype": "技术", "title": "Azure Kubernetes Service 集群无法扩展节点，导致生产环境服务中断",
     "description": "生产环境 AKS 集群扩容节点失败，提示配额不足，服务出现中断。",
     "priority": "P0", "status": "review", "assignee": "张明远", "minutes": 2},
    {"ttype": "技术", "title": "Microsoft 365 Exchange Online 邮件同步失败，影响 200+ 用户",
     "description": "大量用户反馈邮件无法同步，疑似服务事件或 DNS 问题。",
     "priority": "P1", "status": "review", "assignee": "李思琪", "minutes": 5},
    {"ttype": "技术", "title": "Power BI 数据集刷新超时，DirectQuery 模式连接 SQL Server 失败",
     "description": "报表刷新超时，DirectQuery 连接 SQL Server 报错。",
     "priority": "P1", "status": "review", "assignee": "王浩然", "minutes": 8},
    {"ttype": "技术", "title": "SQL Server 2019 数据库备份作业失败，磁盘空间不足",
     "description": "夜间备份作业失败，磁盘空间不足告警。",
     "priority": "P1", "status": "intake", "assignee": None, "minutes": None},
    {"ttype": "技术", "title": "Windows Server 2022 远程桌面许可证过期",
     "description": "用户无法通过远程桌面登录，提示许可证过期。",
     "priority": "P1", "status": "resolved", "assignee": "张明远", "minutes": 12},
    {"ttype": "技术", "title": "Active Directory 域控制器复制失败，错误 8606",
     "description": "域控间复制失败，事件日志报错误 8606。",
     "priority": "P1", "status": "assigned", "assignee": "李思琪", "minutes": 45},
    {"ttype": "产品", "title": "Teams 会议录制文件在哪里查看？如何分享给外部嘉宾？",
     "description": "用户询问会议录制位置和外部分享方法。",
     "priority": "P2", "status": "review", "assignee": None, "minutes": 0},
    {"ttype": "产品", "title": "OneDrive 同步客户端显示「正在处理更改」已持续 2 小时",
     "description": "OneDrive 长时间停留在正在处理更改。",
     "priority": "P2", "status": "review", "assignee": None, "minutes": 3},
    {"ttype": "产品", "title": "SharePoint Online 文档库版本控制如何启用？保留多少个版本？",
     "description": "用户咨询版本控制配置方法。",
     "priority": "P2", "status": "review", "assignee": None, "minutes": 5},
    {"ttype": "产品", "title": "Outlook 邮箱规则设置不生效，邮件未自动分类",
     "description": "设置了规则但邮件没有自动归档。",
     "priority": "P2", "status": "processing", "assignee": None, "minutes": 3},
    {"ttype": "产品", "title": "Microsoft Teams 如何设置会议背景虚化效果",
     "description": "用户咨询背景虚化设置。",
     "priority": "P2", "status": "resolved", "assignee": None, "minutes": 2},
    {"ttype": "技术", "title": "企业网络访问内部系统缓慢，如何排查 VPN 与防火墙",
     "description": "远程办公用户访问内部系统缓慢。",
     "priority": "P1", "status": "classified", "assignee": None, "minutes": None},
]


def seed_technicians():
    conn = get_conn()
    for t in TECHNICIANS:
        exists = conn.execute("SELECT id FROM technicians WHERE name = ?", (t["name"],)).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO technicians (name, title, expertise, skill_tags, load_count) "
                "VALUES (?, ?, ?, ?, ?)",
                (t["name"], t["title"], t["expertise"], t["skill_tags"], 0),
            )
    conn.commit()
    conn.close()


def seed_knowledge():
    conn = get_conn()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for p in SIMULATED_POSTS:
        exists = conn.execute("SELECT id FROM knowledge_articles WHERE kb_id = ?", (p["kb_id"],)).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO knowledge_articles (kb_id, title, content, source, tags, crawled_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (p["kb_id"], p["title"], p["content"], p["source"], ",".join(p["tags"]), now, now),
            )
    conn.commit()
    conn.close()


def seed_tickets():
    conn = get_conn()
    now = datetime.now()
    for i, t in enumerate(SAMPLE_TICKETS):
        ticket_no = f"#{'TK' if t['ttype'] == '技术' else 'PR'}-2024-{8900 + i}"
        exists = conn.execute("SELECT id FROM tickets WHERE ticket_no = ?", (ticket_no,)).fetchone()
        if exists:
            continue
        created = (now - timedelta(minutes=t["minutes"] if t["minutes"] is not None else 60)).strftime(
            "%Y-%m-%d %H:%M:%S")
        conn.execute(
            "INSERT INTO tickets (ticket_no, ttype, title, description, category, priority, tags, status, "
            "assignee_name, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (ticket_no, t["ttype"], t["title"], t["description"],
             "云平台/容器" if "AKS" in t["title"] else "其他",
             t["priority"], "[]", t["status"], t["assignee"], created, created),
        )
    conn.commit()
    conn.close()


def seed_all():
    init_db()
    init_settings()
    seed_technicians()
    seed_knowledge()
    seed_tickets()
    # 重建并持久化向量库
    from stores import rebuild_and_save
    rebuild_and_save()


if __name__ == "__main__":
    seed_all()
    print("数据库初始化完成，向量库已生成。")
