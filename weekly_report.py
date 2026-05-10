"""
Weekly Report - 周报生成器
每周日运行,统计本周胜率 + 下周大事预告
"""
import os
import json
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from database import get_recent_reviews, get_recent_predictions
from data_sources import fetch_calendar
from llm_analyzer import (
    LLM_PROVIDER, _call_gemini, _call_grok,
)


WEEKLY_PROMPT = """你是外汇策略复盘师。基于过去 7 天的预测、复盘数据,以及未来 1 周的经济日历,
生成一份"外汇周报",帮交易者评估系统准确度并提前规划下周。

# 数据

## 过去 7 天预测记录
{predictions}

## 过去 7 天复盘统计
- 总记录数: {total_reviews}
- 最强预测命中数: {strongest_hits} / {total_reviews} = {strongest_rate:.1f}%
- 最弱预测命中数: {weakest_hits} / {total_reviews} = {weakest_rate:.1f}%
- A 级机会盈利天数: {a_tier_hits} / {total_reviews}
- A 级机会平均估算 P&L: {avg_pnl:+.2f}%
- A 级机会累计估算 P&L: {total_pnl:+.2f}%

## 详细复盘记录
{reviews}

## 未来 7 天高影响经济日历
{upcoming}

# 输出格式(中文 Markdown)

# 📊 外汇周报 — {week_label}

## 📈 一、本周系统表现
[2-3 句话总结本周整体准确度。如果胜率 > 60% 就肯定,< 40% 就要承认问题]

## 🎯 二、关键统计
[用 markdown 表格列出胜率、P&L 等核心数据]

## 🔍 三、分析模式洞察
[基于详细复盘记录,识别系统的"擅长"和"短板"。
例如:
- "在央行决议日的预测命中率达到 X%,但在数据日表现一般"
- "对油价相关的 CAD/NOK 预测准确,对 EUR 美元强弱主导的日子偏弱"
找出 1-2 个有意义的模式]

## 📅 四、下周大事预告
[基于未来 7 天日历,列出 5-10 个最值得关注的高影响事件,按时间和重要性排序。
对每个事件用 1 句话标注:潜在影响哪些货币、市场预期是什么、需要警惕什么]

## 🧭 五、下周策略基调
[基于本周表现和下周大事,给出未来一周的整体策略建议:
- 主导主题预判
- 应该重点关注的货币
- 需要规避的不确定性]

## 💡 六、改进建议
[如果本周某些预测错误,反思可能的原因。
例如"周二预测 GBP 最强但实际最强是 EUR,可能因为忽略了 ECB 鸽派讲话的间接影响"。
给出 1-2 条 Prompt 或方法论优化建议(供 Claude 后续参考)]

---

# 重要纪律
- 数据是真实的,不要编造统计
- 如果某些数据为 0(比如首周还没积累),如实说明
- 客观:对自己不准的预测要承认,不要找借口
"""


def generate_weekly_report() -> str:
    """生成本周周报 markdown"""
    reviews = get_recent_reviews(days=7)
    predictions = get_recent_predictions(days=7)

    total = len(reviews)
    strongest_hits = sum(1 for r in reviews if r["strongest_correct"])
    weakest_hits = sum(1 for r in reviews if r["weakest_correct"])
    a_hits = sum(1 for r in reviews if r["a_tier_hit_target"])
    pnls = [r["a_tier_pnl_pct"] for r in reviews if r["a_tier_pnl_pct"] is not None]
    avg_pnl = sum(pnls) / len(pnls) if pnls else 0
    total_pnl = sum(pnls)

    if total == 0:
        return _no_data_report()

    # 格式化数据
    pred_str = "\n".join([
        f"- {p['date']} | 主题: {p['theme'][:50]} | 强:{p['predicted_strongest']} 弱:{p['predicted_weakest']} | A:{p['a_tier_pair']}"
        for p in predictions
    ]) or "(无)"

    rev_str = "\n".join([
        f"- {r['review_date']}: 预测强{predictions[i]['predicted_strongest'] if i < len(predictions) else '?'}→实际强{r['actual_strongest']} {'✅' if r['strongest_correct'] else '❌'} | "
        f"预测弱→实际弱{r['actual_weakest']} {'✅' if r['weakest_correct'] else '❌'} | "
        f"A级 P&L {r['a_tier_pnl_pct']:+.2f}%"
        for i, r in enumerate(reviews)
    ]) or "(无)"

    # 抓未来 7 天日历
    upcoming = fetch_calendar()
    upcoming_str = "\n".join([
        f"- {e['time_bj']} | {e['currency']} | {e['event']} | 影响:{e['impact']} | 预期:{e['forecast'] or 'N/A'}"
        for e in upcoming[:30]
    ]) or "(无重大事件)"

    today = datetime.now(ZoneInfo("Asia/Shanghai"))
    week_label = f"{(today - timedelta(days=6)).strftime('%m-%d')} ~ {today.strftime('%m-%d')}"

    prompt = WEEKLY_PROMPT.format(
        predictions=pred_str,
        total_reviews=total,
        strongest_hits=strongest_hits,
        weakest_hits=weakest_hits,
        strongest_rate=strongest_hits / total * 100 if total else 0,
        weakest_rate=weakest_hits / total * 100 if total else 0,
        a_tier_hits=a_hits,
        avg_pnl=avg_pnl,
        total_pnl=total_pnl,
        reviews=rev_str,
        upcoming=upcoming_str,
        week_label=week_label,
    )

    if LLM_PROVIDER == "grok":
        return _call_grok(prompt)
    else:
        return _call_gemini(prompt)


def _no_data_report() -> str:
    today = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")
    return f"""# 📊 外汇周报 — {today}

本周尚无足够的复盘数据(系统首次运行或刚启动不足一周)。

从下周日开始,周报会自动统计:
- 最强/最弱货币预测命中率
- A 级机会平均盈亏
- 系统擅长/短板的事件类型
- 下周关键事件预告

继续保持每日观察日报,下周日会有第一份完整周报。
"""


if __name__ == "__main__":
    print(generate_weekly_report())
