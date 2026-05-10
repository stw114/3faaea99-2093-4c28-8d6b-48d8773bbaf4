"""
Replay - 昨日复盘逻辑
对照昨日预测 vs 今日实际涨跌,生成复盘文本和评分
"""
from database import (
    get_yesterday_prediction, save_actual_moves, save_review,
)
from market_data import fetch_g10_moves


def generate_review() -> dict:
    """生成对昨日预测的复盘
    返回 dict 包含:
        - has_yesterday: 是否有昨日数据可复盘
        - markdown: 复盘段落(中文 markdown)
        - stats: 评分数据
    """
    yesterday = get_yesterday_prediction()
    if not yesterday:
        return {
            "has_yesterday": False,
            "markdown": "## 📈 一、昨日复盘\n\n首次运行,暂无历史预测可对比。从明日起本板块会自动显示。",
            "stats": {},
        }

    # 抓取实际涨跌
    moves = fetch_g10_moves()
    if not moves:
        return {
            "has_yesterday": True,
            "markdown": (
                "## 📈 一、昨日复盘\n\n"
                "无法获取实际行情数据(yfinance 抓取失败),今日复盘暂缺。"
            ),
            "stats": {},
        }

    save_actual_moves(moves)

    # 排序找出实际最强/最弱
    sorted_moves = sorted(moves.items(), key=lambda x: x[1], reverse=True)
    actual_strongest = sorted_moves[0][0] if sorted_moves else "N/A"
    actual_weakest = sorted_moves[-1][0] if sorted_moves else "N/A"

    pred_strongest = (yesterday.get("predicted_strongest") or "").upper().strip()
    pred_weakest = (yesterday.get("predicted_weakest") or "").upper().strip()

    strongest_correct = pred_strongest == actual_strongest
    weakest_correct = pred_weakest == actual_weakest

    # A 级交叉对的 P&L 估算
    a_pair = yesterday.get("a_tier_pair", "")
    a_dir = (yesterday.get("a_tier_direction") or "").lower()
    a_pnl_pct = 0.0
    if a_pair and "/" in a_pair:
        base, quote = a_pair.split("/")
        base = base.strip().upper()
        quote = quote.strip().upper()
        base_move = moves.get(base, 0)
        quote_move = moves.get(quote, 0)
        # 做多 base/quote = 赚 (base_move - quote_move)
        pair_change = base_move - quote_move
        if "long" in a_dir or "多" in a_dir or "做多" in yesterday.get("a_tier_direction", ""):
            a_pnl_pct = pair_change
        elif "short" in a_dir or "空" in a_dir or "做空" in yesterday.get("a_tier_direction", ""):
            a_pnl_pct = -pair_change

    a_tier_hit = a_pnl_pct > 0

    # 生成 markdown
    icon_strong = "✅" if strongest_correct else "❌"
    icon_weak = "✅" if weakest_correct else "❌"
    icon_pair = "✅" if a_tier_hit else "❌"

    moves_table_lines = []
    for ccy, pct in sorted_moves:
        marker = ""
        if ccy == pred_strongest:
            marker = " ← 昨日预测最强"
        elif ccy == pred_weakest:
            marker = " ← 昨日预测最弱"
        sign = "+" if pct >= 0 else ""
        moves_table_lines.append(f"  - **{ccy}**: {sign}{pct:.2f}%{marker}")

    md = f"""## 📈 一、昨日复盘 (预测日: {yesterday['date']})

**预测最强 {pred_strongest} → 实际最强 {actual_strongest}** {icon_strong}
**预测最弱 {pred_weakest} → 实际最弱 {actual_weakest}** {icon_weak}
**A 级机会 {a_pair} ({yesterday.get('a_tier_direction', '')})**: 估算 P&L **{a_pnl_pct:+.2f}%** {icon_pair}

过去 24 小时 G10 实际涨跌(兑美元):
{chr(10).join(moves_table_lines)}
"""

    review_data = {
        "prediction_date": yesterday["date"],
        "strongest_correct": strongest_correct,
        "weakest_correct": weakest_correct,
        "actual_strongest": actual_strongest,
        "actual_weakest": actual_weakest,
        "a_tier_pnl_pct": a_pnl_pct,
        "a_tier_hit_target": a_tier_hit,
        "notes": f"theme={yesterday.get('theme', '')}",
    }
    save_review(review_data)

    return {
        "has_yesterday": True,
        "markdown": md,
        "stats": review_data,
    }


if __name__ == "__main__":
    result = generate_review()
    print(result["markdown"])
    print("\nStats:", result["stats"])
