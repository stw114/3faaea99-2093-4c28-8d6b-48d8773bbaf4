"""
Database - SQLite 持久化预测和复盘数据
保存路径: data/forex_brief.db
"""
import os
import sqlite3
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

DB_PATH = os.environ.get("DB_PATH", "data/forex_brief.db")


def _ensure_db():
    """确保数据库和表都存在"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL UNIQUE,
        timestamp TEXT NOT NULL,
        theme TEXT,
        predicted_strongest TEXT,
        predicted_weakest TEXT,
        a_tier_pair TEXT,
        a_tier_direction TEXT,
        a_tier_logic TEXT,
        a_tier_target REAL,
        a_tier_stop REAL,
        full_brief TEXT,
        metadata_json TEXT
    );

    CREATE TABLE IF NOT EXISTS actual_moves (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        currency TEXT NOT NULL,
        move_pct REAL NOT NULL,
        measured_at TEXT NOT NULL,
        UNIQUE(date, currency)
    );

    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        review_date TEXT NOT NULL UNIQUE,
        prediction_date TEXT NOT NULL,
        strongest_correct INTEGER,
        weakest_correct INTEGER,
        actual_strongest TEXT,
        actual_weakest TEXT,
        a_tier_pnl_pct REAL,
        a_tier_hit_target INTEGER,
        notes TEXT
    );
    """)
    conn.commit()
    return conn


def save_prediction(metadata: dict, full_brief: str):
    """保存今日预测"""
    conn = _ensure_db()
    today = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")
    now_iso = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()

    a_tier = metadata.get("a_tier", {}) or {}

    def _to_float(v):
        try:
            return float(str(v).replace(",", "").strip()) if v else None
        except (ValueError, TypeError):
            return None

    cur = conn.cursor()
    cur.execute("""
    INSERT OR REPLACE INTO predictions
    (date, timestamp, theme, predicted_strongest, predicted_weakest,
     a_tier_pair, a_tier_direction, a_tier_logic, a_tier_target, a_tier_stop,
     full_brief, metadata_json)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        today, now_iso,
        metadata.get("theme", ""),
        metadata.get("predicted_strongest", ""),
        metadata.get("predicted_weakest", ""),
        a_tier.get("pair", ""),
        a_tier.get("direction", ""),
        a_tier.get("entry_logic", ""),
        _to_float(a_tier.get("target")),
        _to_float(a_tier.get("stop_loss")),
        full_brief,
        json.dumps(metadata, ensure_ascii=False),
    ))
    conn.commit()
    conn.close()


def get_yesterday_prediction():
    """获取昨日(或更早最近一次)的预测"""
    conn = _ensure_db()
    today = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")
    cur = conn.cursor()
    cur.execute("""
    SELECT date, theme, predicted_strongest, predicted_weakest,
           a_tier_pair, a_tier_direction, a_tier_logic, a_tier_target, a_tier_stop,
           metadata_json
    FROM predictions
    WHERE date < ?
    ORDER BY date DESC
    LIMIT 1
    """, (today,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "date": row[0],
        "theme": row[1],
        "predicted_strongest": row[2],
        "predicted_weakest": row[3],
        "a_tier_pair": row[4],
        "a_tier_direction": row[5],
        "a_tier_logic": row[6],
        "a_tier_target": row[7],
        "a_tier_stop": row[8],
        "metadata": json.loads(row[9]) if row[9] else {},
    }


def save_actual_moves(moves: dict):
    """保存今日各货币 24h 涨跌"""
    conn = _ensure_db()
    today = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")
    now_iso = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()
    cur = conn.cursor()
    for currency, pct in moves.items():
        cur.execute("""
        INSERT OR REPLACE INTO actual_moves (date, currency, move_pct, measured_at)
        VALUES (?, ?, ?, ?)
        """, (today, currency, float(pct), now_iso))
    conn.commit()
    conn.close()


def save_review(review: dict):
    """保存对昨日预测的复盘"""
    conn = _ensure_db()
    today = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")
    cur = conn.cursor()
    cur.execute("""
    INSERT OR REPLACE INTO reviews
    (review_date, prediction_date, strongest_correct, weakest_correct,
     actual_strongest, actual_weakest, a_tier_pnl_pct, a_tier_hit_target, notes)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        today,
        review.get("prediction_date", ""),
        1 if review.get("strongest_correct") else 0,
        1 if review.get("weakest_correct") else 0,
        review.get("actual_strongest", ""),
        review.get("actual_weakest", ""),
        review.get("a_tier_pnl_pct", 0.0),
        1 if review.get("a_tier_hit_target") else 0,
        review.get("notes", ""),
    ))
    conn.commit()
    conn.close()


def get_recent_reviews(days: int = 7) -> list:
    """取最近 N 天的复盘记录(用于周报统计)"""
    conn = _ensure_db()
    cutoff = (datetime.now(ZoneInfo("Asia/Shanghai")) - timedelta(days=days)).strftime("%Y-%m-%d")
    cur = conn.cursor()
    cur.execute("""
    SELECT review_date, prediction_date, strongest_correct, weakest_correct,
           actual_strongest, actual_weakest, a_tier_pnl_pct, a_tier_hit_target, notes
    FROM reviews
    WHERE review_date >= ?
    ORDER BY review_date DESC
    """, (cutoff,))
    rows = cur.fetchall()
    conn.close()
    return [{
        "review_date": r[0],
        "prediction_date": r[1],
        "strongest_correct": bool(r[2]),
        "weakest_correct": bool(r[3]),
        "actual_strongest": r[4],
        "actual_weakest": r[5],
        "a_tier_pnl_pct": r[6],
        "a_tier_hit_target": bool(r[7]),
        "notes": r[8],
    } for r in rows]


def get_recent_predictions(days: int = 7) -> list:
    """取最近 N 天的预测(用于周报)"""
    conn = _ensure_db()
    cutoff = (datetime.now(ZoneInfo("Asia/Shanghai")) - timedelta(days=days)).strftime("%Y-%m-%d")
    cur = conn.cursor()
    cur.execute("""
    SELECT date, theme, predicted_strongest, predicted_weakest,
           a_tier_pair, a_tier_direction
    FROM predictions
    WHERE date >= ?
    ORDER BY date DESC
    """, (cutoff,))
    rows = cur.fetchall()
    conn.close()
    return [{
        "date": r[0],
        "theme": r[1],
        "predicted_strongest": r[2],
        "predicted_weakest": r[3],
        "a_tier_pair": r[4],
        "a_tier_direction": r[5],
    } for r in rows]


if __name__ == "__main__":
    # 测试
    _ensure_db()
    print(f"数据库已初始化: {DB_PATH}")
