"""全局配置：路径、默认设置、设置读写。

所有可配置项都存入 SQLite 的 settings 表，后台「系统设置」页面可灵活修改，
例如大模型 provider / base_url / api_key / model，以及向量库与爬虫调度配置。
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
os.makedirs(DATA_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "support_agent.db")
VECTOR_PATH = os.path.join(DATA_DIR, "vectors.json")

# 默认设置（首次初始化时写入 settings 表）
DEFAULT_SETTINGS = {
    # 大模型配置（支持 OpenAI 兼容协议：OpenAI / DeepSeek / Qwen / Ollama 等）
    "llm_provider": "deepseek",                # mock=内置规则；deepseek/openai=OpenAI兼容协议
    "llm_base_url": "https://api.deepseek.com",
    # 密钥不入库：优先读取环境变量，也可在后台「系统设置」页面填写（写入本地 SQLite）
    "llm_api_key": os.environ.get("LLM_API_KEY", ""),
    "llm_model": "deepseek-flash",
    "llm_temperature": "0.3",
    # 向量库配置（local=轻量本地哈希向量；openai=调用 embedding 接口）
    "embedding_provider": "local",
    "embedding_model": "text-embedding-3-small",
    "vector_dim": "512",
    # 自动处理中心
    "auto_reply_confidence_threshold": "0.7",
    "assign_top_k": "3",
    # 爬虫调度
    "crawl_enabled": "true",
    "crawl_schedule": "0 2 * * *",             # 每天 02:00 增量爬取
    "crawl_forum_url": "",                     # 正式环境：企业内部论坛地址
}


def _get_conn():
    # 延迟导入，避免循环依赖
    from db import get_conn
    return get_conn()


def init_settings():
    """把默认设置写入 settings 表（不覆盖已有值）。"""
    from db import get_conn
    conn = get_conn()
    conn.executemany(
        "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
        list(DEFAULT_SETTINGS.items()),
    )
    conn.commit()
    conn.close()


def get_all_settings():
    from db import get_conn
    conn = get_conn()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    data = {r["key"]: r["value"] for r in rows}
    # 合并默认值，保证缺失项也有值
    merged = dict(DEFAULT_SETTINGS)
    merged.update(data)
    return merged


def get_setting(key, default=None):
    from db import get_conn
    conn = get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    if row is None:
        return DEFAULT_SETTINGS.get(key, default)
    return row["value"]


def set_settings(items):
    """items: dict，批量更新设置。"""
    from db import get_conn
    conn = get_conn()
    conn.executemany(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        list(items.items()),
    )
    conn.commit()
    conn.close()
