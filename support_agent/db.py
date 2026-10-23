"""SQLite 数据层：连接与建表。"""
import sqlite3

from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS technicians (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    email        TEXT,
    title        TEXT,
    expertise    TEXT NOT NULL,          -- 擅长领域描述（进入向量库）
    skill_tags   TEXT,                   -- 逗号分隔标签
    load_count   INTEGER DEFAULT 0,      -- 当前在办工单数（负载）
    is_active    INTEGER DEFAULT 1,
    created_at   TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS knowledge_articles (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    kb_id      TEXT UNIQUE,             -- 如 KB-4421
    title      TEXT NOT NULL,
    content    TEXT NOT NULL,
    source     TEXT,                    -- 来源：论坛/帮助中心
    source_url TEXT,
    tags       TEXT,
    crawled_at TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS tickets (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_no    TEXT UNIQUE,
    ttype        TEXT,                  -- 技术 / 产品
    title        TEXT NOT NULL,
    description  TEXT,
    category     TEXT,                  -- 分类
    priority     TEXT,                  -- P0/P1/P2
    tags         TEXT,
    status       TEXT,                  -- 见 workflow.STATUS_*
    source       TEXT,
    assignee_id  INTEGER,
    assignee_name TEXT,
    match_score  REAL,
    candidates   TEXT,                  -- 推荐技术人（JSON）
    auto_reply   TEXT,                  -- Agent 自动回复内容
    reply_confidence REAL,              -- 置信度 0~1
    reply_sources TEXT,                 -- 命中的知识库来源（JSON）
    reject_reason TEXT,
    created_at   TEXT DEFAULT (datetime('now', 'localtime')),
    updated_at   TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS workflow_logs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id  INTEGER,
    node       TEXT,                    -- 工单接入/智能分类/自动处理分派/人工评估/解决闭环
    action     TEXT,
    detail     TEXT,
    operator   TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS crawl_jobs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    source       TEXT,
    status       TEXT,                  -- running / success / failed
    new_count    INTEGER DEFAULT 0,
    updated_count INTEGER DEFAULT 0,
    message      TEXT,
    started_at   TEXT DEFAULT (datetime('now', 'localtime')),
    finished_at  TEXT
);
"""


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
