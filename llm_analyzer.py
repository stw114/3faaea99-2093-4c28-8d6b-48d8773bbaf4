"""
LLM Analyzer - Gemini API 分析,输出更丰富的 metadata 以匹配前端 React mock
"""
import os
import re
import json
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "gemini").lower()
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
XAI_API_KEY = os.environ.get("XAI_API_KEY", "")
XAI_MODEL = os.environ.get("XAI_MODEL", "grok-4")

METADATA_MARKER = "===METADATA==="

ANALYSIS_PROMPT = """你是专业的外汇宏观策略师,服务于一位活跃的零售外汇交易者。
任务:基于真实数据,产出"欧洲盘开盘前简报",锁定**今日波动最大的货币和最有把握的交叉对**。

# 核心方法论(严格遵守)

## G10 货币对主题敏感度对照表
| 主题 | 高 Beta | 中 Beta | 低 Beta |
|---|---|---|---|
| 原油涨跌 | CAD, NOK | AUD, MXN | CHF, JPY, EUR |
| 风险偏好切换 | AUD, NZD | CAD, SEK | CHF, JPY, USD |
| 美元强弱 | EUR(权重大) | GBP, JPY | CHF |
| 中国数据/大宗 | AUD, NZD | CAD | CHF, EUR |
| 避险/地缘冲突 | JPY, CHF(涨) | USD | AUD, NZD(跌) |
| 美联储鸽鹰转向 | USD 全面 | EUR, JPY | CHF |
| 欧央行 | EUR | GBP | 其他 |
| 日央行 | JPY | 其他 | - |
| 英央行 | GBP | EUR | 其他 |

## 分析三步法
1. **找主题**: 当前最重要的 1-2 个驱动?
2. **找最强 Beta**: 对照表找最敏感货币
3. **找催化剂叠加**: 该货币本日是否还有本地催化剂?

## 选交叉对原则
**最大波动出现在"最弱货币 vs 最强货币"的直接交叉对上**。

---

# 你拿到的数据

## 经济日历(未来 24-36 小时高/中影响事件)
{calendar}

## 过去 24 小时关键新闻
{news}

## 当前市场状态指标
{market_state}

## 主要货币对技术位置
{technical_levels}

---

# 输出格式

先输出一段 markdown 简报(中文,简短即可,前端不显示这部分,只用作邮件备份)。

然后在文末输出 ===METADATA=== 后跟一个完整 JSON,**严格按下面 schema 输出,字段名一字不差**:

```json
{{
  "theme": "今日核心主题(15-25字一句话)",
  "theme_detail": "主题详细解读(40-80字)",
  "predicted_strongest": "AUD",
  "strongest_reason": "高Beta于风险偏好回归(15-25字)",
  "predicted_weakest": "CAD",
  "weakest_reason": "油价崩盘+央行偏鸽(15-25字)",
  "predicted_secondary_strong": "NZD",
  "secondary_strong_reason": "跟随澳元商品货币强势(15字)",
  "predicted_secondary_weak": "USD",
  "secondary_weak_reason": "避险溢价回吐(15字)",
  "a_tier": {{
    "pair": "AUD/CAD",
    "direction": "long",
    "entry_logic": "最强vs最弱直接对子,双重催化剂叠加(20-40字)",
    "entry": "0.9050",
    "stop_loss": "0.8990",
    "target": "0.9120",
    "tp2": "0.9180",
    "trigger_condition": "0.9050阻力上破"
  }},
  "b_tier": {{
    "pair": "AUD/JPY",
    "direction": "long",
    "entry_logic": "Risk-on经典对(20-40字)",
    "entry": "101.80",
    "stop_loss": "101.10",
    "target": "102.80",
    "tp2": "103.50"
  }},
  "c_tier": {{
    "pair": "USD/CAD",
    "direction": "short",
    "entry_logic": "次选,带美元信号稀释(20字)",
    "entry": "1.3720",
    "stop_loss": "1.3780",
    "target": "1.3640",
    "tp2": "1.3580"
  }},
  "risks": [
    "若Waller发表鹰派言论,USD空头可能被快速止损,AUD/CAD回调至0.9000",
    "加拿大就业数据若意外走弱,CAD强势逻辑当日失效,建议等数据后入场"
  ],
  "best_session": "16:30—21:00",
  "stop_loss_rule": "≤账户 1%",
  "wait_catalyst": "建议等",
  "position_size": "半仓起"
}}
```

# 重要纪律
1. **货币代码用大写**(AUD, CAD, USD, EUR, GBP, JPY, CHF, NZD, SEK, NOK)
2. **direction 字段只能是 "long" 或 "short"**
3. **价格用字符串(带小数点)**,如 "0.9050",不要写 0.9050(数字)
4. **风险列表 risks 必须是 2 条**,每条 30-50 字,真实可验证
5. **a_tier/b_tier/c_tier 三个都要填**,c_tier 通常用带美元的对子作次选
6. **基于真实数据**,价格点位必须来自上方提供的"主要货币对技术位置"
7. **绝不编造**,信息不足时把对应字段填空字符串 ""
"""


def _call_gemini(prompt: str) -> str:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY 未设置")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 8192},
    }
    resp = requests.post(f"{url}?key={GEMINI_API_KEY}", json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _call_grok(prompt: str) -> str:
    if not XAI_API_KEY:
        raise ValueError("XAI_API_KEY 未设置")
    url = "https://api.x.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {XAI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": XAI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3, "max_tokens": 8192,
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def _format_market_state(market: dict) -> str:
    if not market:
        return "(无)"
    lines = []
    for key, info in market.items():
        sign = "+" if info["change_pct"] >= 0 else ""
        lines.append(f"- {info['label']}: {info['value']:.4f} ({sign}{info['change_pct']:.2f}%)")
    return "\n".join(lines)


def _format_levels(levels: dict) -> str:
    if not levels:
        return "(无)"
    lines = []
    for pair, lv in levels.items():
        lines.append(
            f"- {pair}: 现价{lv['latest']:.4f} | 20D高{lv['high_20d']:.4f}/低{lv['low_20d']:.4f} | "
            f"SMA20 {lv['sma_20']:.4f} | SMA50 {lv['sma_50']:.4f} | "
            f"R1 {lv['r1']:.4f} | R2 {lv['r2']:.4f} | S1 {lv['s1']:.4f} | S2 {lv['s2']:.4f}"
        )
    return "\n".join(lines)


def parse_metadata(text: str):
    """从 LLM 输出拆分 markdown 和 JSON metadata"""
    if METADATA_MARKER not in text:
        # 也可能 LLM 直接输出了 JSON,试试找 ```json
        match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            try:
                return text, json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        return text, {}

    parts = text.split(METADATA_MARKER, 1)
    markdown = parts[0].strip()
    meta_raw = parts[1].strip()
    meta_raw = re.sub(r"^```(?:json)?\s*", "", meta_raw)
    meta_raw = re.sub(r"\s*```\s*$", "", meta_raw)

    try:
        metadata = json.loads(meta_raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", meta_raw, re.DOTALL)
        if match:
            try:
                metadata = json.loads(match.group(0))
            except json.JSONDecodeError:
                metadata = {}
        else:
            metadata = {}
    return markdown, metadata


def analyze_forex_opportunities(calendar, news, market_state, technical_levels):
    if calendar:
        calendar_str = "\n".join([
            f"- {e['time_bj']} | {e['currency']} | {e['event']} | "
            f"影响:{e['impact']} | 预期:{e['forecast'] or 'N/A'} | 前值:{e['previous'] or 'N/A'}"
            for e in calendar
        ])
    else:
        calendar_str = "(无)"

    if news:
        news_str = "\n".join([f"- {n['time_bj']} {n['title']}" for n in news[:25]])
    else:
        news_str = "(无)"

    prompt = ANALYSIS_PROMPT.format(
        calendar=calendar_str,
        news=news_str,
        market_state=_format_market_state(market_state),
        technical_levels=_format_levels(technical_levels),
    )

    raw = _call_grok(prompt) if LLM_PROVIDER == "grok" else _call_gemini(prompt)
    return parse_metadata(raw)


if __name__ == "__main__":
    print(analyze_forex_opportunities([], [], {}, {}))
