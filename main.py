"""
Forex Daily Brief - 主入口
模式:
  --mode daily   : 生成日报 + 邮件 + 写入 JSON
  --mode weekly  : 生成周报 + 邮件
  --mode export  : 仅重新生成 JSON(不调用 LLM,从数据库读最新)
"""
import os
import sys
import json
import argparse
import traceback
from datetime import datetime
from zoneinfo import ZoneInfo


def get_bj_time():
    return datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M")


def run_daily(skip_email: bool = False):
    from data_sources import fetch_calendar, fetch_news
    from market_data import fetch_market_state, fetch_all_pair_levels, fetch_g10_moves
    from llm_analyzer import analyze_forex_opportunities
    from replay import generate_review
    from database import save_prediction
    from json_exporter import build_today_payload, export_all
    from emailer import send_email

    print(f"[{get_bj_time()}] 开始生成日报...")

    print("步骤 1/6: 昨日复盘...")
    try:
        review = generate_review()
        print(f"  ✓ 复盘 (has_yesterday={review['has_yesterday']})")
    except Exception as e:
        print(f"  ✗ 复盘出错: {e}")
        review = {"has_yesterday": False, "markdown": "", "stats": {}}

    print("步骤 2/6: 抓取数据...")
    try:
        calendar = fetch_calendar()
        news = fetch_news()
        market_state = fetch_market_state()
        levels = fetch_all_pair_levels()
        actual_moves = fetch_g10_moves()
        print(f"  ✓ 日历{len(calendar)} 新闻{len(news)} 市场{len(market_state)} 技术{len(levels)} G10{len(actual_moves)}")
    except Exception as e:
        print(f"  ✗ 抓取失败: {e}")
        traceback.print_exc()
        calendar, news, market_state, levels, actual_moves = [], [], {}, {}, {}

    print("步骤 3/6: LLM 分析...")
    try:
        analysis_md, metadata = analyze_forex_opportunities(calendar, news, market_state, levels)
        print(f"  ✓ 分析完成 metadata={len(metadata)} 字段")
    except Exception as e:
        print(f"  ✗ 分析失败: {e}")
        traceback.print_exc()
        analysis_md, metadata = "", {}

    print("步骤 4/6: 落库 + 构造 JSON...")
    full_brief = (review["markdown"] + "\n\n---\n\n" + analysis_md) if review["markdown"] else analysis_md
    try:
        if metadata:
            save_prediction(metadata, full_brief)
        today_payload = build_today_payload(
            metadata, full_brief, market_state, levels, calendar, actual_moves
        )
        output_dir = os.environ.get("JSON_OUTPUT_DIR", "site/data")
        files = export_all(today_payload, output_dir)
        print(f"  ✓ JSON 写入: {output_dir}")
        for k, v in files.items():
            print(f"    - {k}: {v}")
    except Exception as e:
        print(f"  ✗ 导出失败: {e}")
        traceback.print_exc()

    if skip_email:
        print("步骤 5-6: 跳过邮件(--no-email)")
        print(f"[{get_bj_time()}] 完成 ✓")
        return

    print("步骤 5/6: 发送邮件...")
    today = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d (%a)")
    subject = f"📊 外汇日报 {today} — 欧洲盘开盘前简报"
    try:
        send_email(subject, full_brief or analysis_md or "今日数据抓取异常,请查看日志")
        print(f"  ✓ 邮件发送")
    except Exception as e:
        print(f"  ✗ 邮件失败: {e}")

    print("步骤 6/6: Git 推送(如果配置了)...")
    if os.environ.get("AUTO_GIT_PUSH", "").lower() == "true":
        try:
            os.system("cd site && git add -A && git commit -m 'auto: daily update' && git push")
            print(f"  ✓ 已推送到 GitHub")
        except Exception as e:
            print(f"  ✗ Git 推送失败: {e}")
    else:
        print(f"  - Git 推送已禁用(AUTO_GIT_PUSH != true)")

    print(f"[{get_bj_time()}] 完成 ✓")


def run_weekly():
    from weekly_report import generate_weekly_report
    from emailer import send_email
    print(f"[{get_bj_time()}] 周报...")
    try:
        report_md = generate_weekly_report()
        today = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")
        send_email(f"📈 外汇周报 {today}", report_md)
        print(f"[{get_bj_time()}] 周报完成 ✓")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        traceback.print_exc()
        sys.exit(1)


def run_export_only():
    """仅从已有数据库导出 JSON,不调用 LLM"""
    from database import _ensure_db, get_recent_predictions
    from json_exporter import build_today_payload, export_all
    from market_data import fetch_market_state, fetch_all_pair_levels, fetch_g10_moves
    from data_sources import fetch_calendar

    _ensure_db()
    print(f"[{get_bj_time()}] 仅导出 JSON 模式...")

    preds = get_recent_predictions(days=1)
    if not preds:
        print("  数据库中无最近预测,生成 demo payload")
        from seed_demo import build_demo_payload
        payload = build_demo_payload()
    else:
        latest = preds[0]
        metadata = latest.get("metadata", {}) or {}
        try:
            market = fetch_market_state()
            levels = fetch_all_pair_levels()
            cal = fetch_calendar()
            moves = fetch_g10_moves()
        except Exception:
            market, levels, cal, moves = {}, {}, [], {}
        payload = build_today_payload(metadata, "", market, levels, cal, moves)

    out_dir = os.environ.get("JSON_OUTPUT_DIR", "site/data")
    files = export_all(payload, out_dir)
    print(f"  ✓ 导出到 {out_dir}")
    for k, v in files.items():
        print(f"    - {k}: {v}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["daily", "weekly", "export"], default="daily")
    parser.add_argument("--no-email", action="store_true", help="跳过邮件发送")
    args = parser.parse_args()

    if args.mode == "daily":
        run_daily(skip_email=args.no_email)
    elif args.mode == "weekly":
        run_weekly()
    elif args.mode == "export":
        run_export_only()
