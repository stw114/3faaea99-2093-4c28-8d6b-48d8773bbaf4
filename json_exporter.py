import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo

def build_today_payload(metadata: dict, full_brief: str, market_state: dict, levels: dict, calendar: list, actual_moves: dict) -> dict:
    now_str = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M:%S")
    return {
        "update_time": now_str,
        "metadata": metadata,
        "full_brief": full_brief,
        "market_state": market_state,
        "technical_levels": levels,
        "calendar": calendar,
        "actual_moves": actual_moves
    }

def export_all(today_payload: dict, output_dir: str) -> dict:
    os.makedirs(output_dir, exist_ok=True)
    files_created = {}
    today_file = os.path.join(output_dir, "today.json")
    with open(today_file, "w", encoding="utf-8") as f:
        json.dump(today_payload, f, ensure_ascii=False, indent=2)

    files_created["today"] = today_file
    date_str = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")
    archive_file = os.path.join(output_dir, f"{date_str}.json")
    with open(archive_file, "w", encoding="utf-8") as f:
        json.dump(today_payload, f, ensure_ascii=False, indent=2)
    files_created["archive"] = archive_file
    return files_created

