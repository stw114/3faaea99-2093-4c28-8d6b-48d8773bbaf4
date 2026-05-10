"""
Data Sources - 从免费公共数据源抓取外汇日历和新闻
- Forex Factory 经济日历(JSON)
- ForexLive 新闻 RSS
- Investing.com 备用源
"""
import requests
import feedparser
from datetime import datetime, timedelta, timezone

# Forex Factory 本周经济日历(JSON 格式,免费)
FF_CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

# ForexLive 新闻 RSS
FORExLIVE_RSS = "https://www.forexlive.com/feed/news/"

# 备用:Investing.com economic calendar
DAILYFX_RSS = "https://www.dailyfx.com/feeds/market-news"

# HTTP 请求头(避免被反爬)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def fetch_calendar():
    """
    抓取未来 36 小时内的高/中影响经济日历事件
    返回结构化列表
    """
    try:
        resp = requests.get(FF_CALENDAR_URL, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        events = resp.json()
    except Exception as e:
        print(f"日历抓取失败: {e}")
        return []

    now = datetime.now(timezone.utc)
    cutoff = now + timedelta(hours=36)

    relevant = []
    for event in events:
        # 解析事件时间(Forex Factory 格式: "2026-05-09T13:30:00-04:00")
        try:
            date_str = event.get("date", "")
            if not date_str:
                continue
            event_date = datetime.fromisoformat(date_str)
            if event_date.tzinfo is None:
                event_date = event_date.replace(tzinfo=timezone.utc)
        except Exception:
            continue

        if not (now <= event_date <= cutoff):
            continue

        impact = event.get("impact", "").lower()
        if impact not in ("high", "medium"):
            continue

        # 转换成北京时间方便阅读
        bj_time = event_date.astimezone(timezone(timedelta(hours=8)))
        relevant.append({
            "time_utc": event_date.strftime("%Y-%m-%d %H:%M UTC"),
            "time_bj": bj_time.strftime("%m-%d %H:%M (北京)"),
            "currency": event.get("country", ""),
            "event": event.get("title", ""),
            "impact": event.get("impact", ""),
            "forecast": event.get("forecast", ""),
            "previous": event.get("previous", ""),
        })

    # 按时间排序
    relevant.sort(key=lambda x: x["time_utc"])
    return relevant


def fetch_news(hours=24, max_items=30):
    """
    抓取过去 N 小时的外汇新闻头条
    """
    news_items = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    sources = [
        ("ForexLive", FORExLIVE_RSS),
        ("DailyFX", DAILYFX_RSS),
    ]

    for source_name, url in sources:
        try:
            feed = feedparser.parse(url, request_headers=HEADERS)
            for entry in feed.entries[:40]:
                try:
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    else:
                        continue

                    if published < cutoff:
                        continue

                    # 转北京时间
                    bj = published.astimezone(timezone(timedelta(hours=8)))
                    news_items.append({
                        "time_bj": bj.strftime("%m-%d %H:%M"),
                        "source": source_name,
                        "title": entry.title,
                        "summary": (entry.get("summary", "") or "")[:200],
                    })
                except Exception:
                    continue
        except Exception as e:
            print(f"  RSS 源 {source_name} 失败: {e}")
            continue

    # 按时间倒序(最新在前)
    news_items.sort(key=lambda x: x["time_bj"], reverse=True)
    return news_items[:max_items]


if __name__ == "__main__":
    # 本地测试用
    print("=== 测试日历 ===")
    cal = fetch_calendar()
    for e in cal[:10]:
        print(f"{e['time_bj']} | {e['currency']} | {e['event']} | 影响:{e['impact']}")

    print("\n=== 测试新闻 ===")
    news = fetch_news()
    for n in news[:10]:
        print(f"{n['time_bj']} [{n['source']}] {n['title']}")
