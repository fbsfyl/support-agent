"""后台定时调度：按 cron 表达式定时增量爬取知识库。

- 读取 settings.crawl_enabled / settings.crawl_schedule。
- 内置轻量 cron 匹配（5 字段：分 时 日 月 周），无需额外依赖。
- 每 20 秒轮询一次，命中且当前分钟未执行过则触发 run_crawl()。
"""
import threading
import time
from datetime import datetime

from config import get_setting

_SCHEDULER_STARTED = False
_stop_event = threading.Event()


def _match_field(value, actual):
    """匹配单个 cron 字段，支持 *、*/step、a-b、a,b,c。"""
    value = str(value).strip()
    if value == "*":
        return True
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            if part.startswith("*/"):
                step = int(part[2:])
                if step > 0 and actual % step == 0:
                    return True
            elif "-" in part:
                a, b = part.split("-", 1)
                if int(a) <= actual <= int(b):
                    return True
            else:
                if int(part) == actual:
                    return True
        except (ValueError, IndexError):
            continue
    return False


def cron_matches(expr, now=None):
    """判断当前时间是否命中 5 字段 cron 表达式。"""
    now = now or datetime.now()
    fields = [f.strip() for f in str(expr).split()]
    if len(fields) != 5:
        return False
    minute, hour, dom, mon, dow = fields
    # cron 周日=0；datetime.weekday() 周一=0，故用 (weekday+1)%7 映射
    checks = [
        (minute, now.minute),
        (hour, now.hour),
        (dom, now.day),
        (mon, now.month),
        (dow, (now.weekday() + 1) % 7),
    ]
    return all(_match_field(v, a) for v, a in checks)


def _loop():
    last_run = None  # (年, 月, 日, 时, 分)
    while not _stop_event.is_set():
        try:
            enabled = str(get_setting("crawl_enabled", "true")).lower() in ("1", "true", "yes", "on")
            if enabled:
                now = datetime.now()
                expr = get_setting("crawl_schedule", "0 2 * * *")
                key = (now.year, now.month, now.day, now.hour, now.minute)
                if cron_matches(expr, now) and key != last_run:
                    last_run = key
                    try:
                        from crawler.crawler import run_crawl
                        run_crawl()
                    except Exception:
                        pass
        except Exception:
            pass
        _stop_event.wait(20)


def start_scheduler():
    """启动后台定时调度线程（幂等，重复调用只启动一次）。"""
    global _SCHEDULER_STARTED
    if _SCHEDULER_STARTED:
        return
    _SCHEDULER_STARTED = True
    t = threading.Thread(target=_loop, name="crawl-scheduler", daemon=True)
    t.start()
