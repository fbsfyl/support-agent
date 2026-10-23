"""可配置大模型客户端。

- 后台「系统设置」可灵活切换 provider / base_url / api_key / model。
- 当未配置 api_key 或 provider=mock 时，自动降级为内置规则，保证开箱即可运行。
"""
import re

from config import get_all_settings


def get_llm_config():
    s = get_all_settings()
    return {
        "provider": s.get("llm_provider", "mock"),
        "base_url": s.get("llm_base_url", ""),
        "api_key": s.get("llm_api_key", ""),
        "model": s.get("llm_model", "gpt-4o-mini"),
        "temperature": float(s.get("llm_temperature", "0.3") or 0.3),
        "embedding_provider": s.get("embedding_provider", "local"),
        "embedding_model": s.get("embedding_model", "text-embedding-3-small"),
    }


def llm_ready():
    c = get_llm_config()
    return c["provider"] != "mock" and bool(c.get("api_key"))


def _openai_client():
    from openai import OpenAI
    c = get_llm_config()
    return OpenAI(api_key=c["api_key"], base_url=c["base_url"] or None)


def chat(messages, temperature=None):
    """调用大模型，返回文本；不可用返回 None。"""
    if not llm_ready():
        return None
    c = get_llm_config()
    try:
        client = _openai_client()
        resp = client.chat.completions.create(
            model=c["model"],
            messages=messages,
            temperature=temperature if temperature is not None else c["temperature"],
        )
        return resp.choices[0].message.content
    except Exception:
        return None


def embed_texts(texts):
    """返回向量列表；若配置了 openai embedding 则调用，否则返回 None（用本地哈希向量）。"""
    c = get_llm_config()
    if c["embedding_provider"] == "openai" and bool(c.get("api_key")):
        try:
            client = _openai_client()
            resp = client.embeddings.create(
                model=c["embedding_model"] or "text-embedding-3-small", input=texts
            )
            return [d.embedding for d in resp.data]
        except Exception:
            return None
    return None


# ---------------- 内置规则（mock 降级） ----------------

_TECH_KEYWORDS = [
    "服务器", "数据库", "网络", "集群", "kubernetes", "k8s", "azure", "aks",
    "sql", "active directory", "域控", "域控制器", "docker", "容器", "防火墙",
    "vpn", "linux", "windows server", "部署", "宕机", "备份", "磁盘", "证书",
    "dns", "api", "负载均衡", "节点", "许可", "许可证",
]

_PRODUCT_KEYWORDS = [
    "teams", "outlook", "onedrive", "sharepoint", "power bi", "excel", "word",
    "邮箱", "邮件", "会议", "录制", "同步", "版本控制", "规则", "背景虚化",
]


def _category_and_tags(title, description, ttype):
    text = (title + " " + (description or "")).lower()
    if ttype == "技术":
        mapping = [
            ("云平台/容器", ["azure", "aks", "kubernetes", "k8s", "docker", "容器", "集群", "节点", "负载均衡"]),
            ("数据库", ["sql", "数据库", "备份", "磁盘", "directquery", "数据集"]),
            ("网络/安全", ["网络", "防火墙", "vpn", "dns", "证书", "安全"]),
            ("服务器/AD", ["服务器", "windows server", "active directory", "域控", "许可", "许可证", "远程桌面"]),
        ]
    else:
        mapping = [
            ("协作办公", ["teams", "outlook", "邮箱", "邮件", "会议", "录制", "背景虚化", "规则"]),
            ("云存储", ["onedrive", "sharepoint", "同步", "版本控制", "文档库"]),
            ("数据分析", ["power bi", "数据集", "directquery", "报表"]),
        ]
    tags = []
    for cat, kws in mapping:
        for kw in kws:
            if kw in text:
                tags.append(kw)
                break
    category = next((c for c, kws in mapping if any(k in text for k in kws)), "其他")
    return category, tags[:4]


def classify_ticket(title, description):
    """返回 {ttype, category, priority, tags, confidence}。优先走大模型，失败则规则。"""
    text = (title + " " + (description or "")).lower()

    # 尝试大模型分类
    prompt = (
        "你是 IT 工单分类助手。请将以下工单分类，只返回 JSON，不要多余文字：\n"
        '{"ttype": "技术"或"产品", "category": "分类名", "priority": "P0/P1/P2", '
        '"tags": ["标签1","标签2"], "confidence": 0.0~1.0}\n\n'
        f"标题：{title}\n描述：{description}"
    )
    llm_out = chat([{"role": "user", "content": prompt}])
    if llm_out:
        import json
        m = re.search(r"\{.*\}", llm_out, re.S)
        if m:
            try:
                data = json.loads(m.group(0))
                data.setdefault("category", "其他")
                data.setdefault("priority", "P2")
                data.setdefault("tags", [])
                data.setdefault("confidence", 0.8)
                return data
            except Exception:
                pass

    # 规则降级
    if any(k in text for k in _TECH_KEYWORDS):
        ttype = "技术"
    elif any(k in text for k in _PRODUCT_KEYWORDS):
        ttype = "产品"
    else:
        ttype = "产品"

    category, tags = _category_and_tags(title, description, ttype)

    urgent = ["中断", "宕机", "无法", "瘫痪", "失败", "生产", "停止", "超时"]
    if any(k in text for k in urgent) or ttype == "技术":
        priority = "P1"
    else:
        priority = "P2"
    if any(k in text for k in ["中断", "宕机", "瘫痪", "生产环境", "服务中断"]):
        priority = "P0"

    return {"ttype": ttype, "category": category, "priority": priority,
            "tags": tags, "confidence": 0.78}


def generate_reply(query, context_texts):
    """基于知识库上下文生成自动回复。优先大模型，失败则模板。"""
    ctx = "\n\n".join(context_texts[:3]) if context_texts else "（未命中知识库）"
    prompt = (
        "你是企业内部 IT 支持 Agent。请依据下面的知识库内容回答用户问题，"
        "要求：分步骤、专业、简洁。若知识库不足请如实说明。\n\n"
        f"用户问题：{query}\n\n知识库内容：\n{ctx}"
    )
    out = chat([{"role": "user", "content": prompt}])
    if out:
        return out
    if context_texts:
        return (
            "根据内部知识库，建议按以下步骤处理：\n"
            + "\n".join(f"{i+1}) {t[:120]}" for i, t in enumerate(context_texts[:3]))
        )
    return "暂未在内部知识库找到匹配答案，建议转人工处理。"
