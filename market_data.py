"""
Market Data - 抓取市场状态指标和 G10 实际涨跌
使用 yfinance(免费、无需 API key)
"""
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

try:
    import yfinance as yf
    YF_AVAILABLE = True
except ImportError:
    YF_AVAILABLE = False
    print("警告: yfinance 未安装,市场数据功能不可用")


# 市场状态指标
MARKET_TICKERS = {
    "DXY":   ("DX-Y.NYB", "美元指数"),
    "VIX":   ("^VIX",     "VIX 恐慌指数"),
    "WTI":   ("CL=F",     "WTI 原油"),
    "BRENT": ("BZ=F",     "布伦特原油"),
    "US10Y": ("^TNX",     "美 10 年期国债收益率"),
    "GOLD":  ("GC=F",     "黄金"),
    "SP500": ("^GSPC",    "标普 500"),
}

# G10 货币对(以 USD 为基准)
# (currency_code, ticker, is_inverted) - is_inverted 表示 ticker 是 USD/XXX 而非 XXX/USD
G10_PAIRS = [
    ("EUR", "EURUSD=X", False),
    ("GBP", "GBPUSD=X", False),
    ("JPY", "USDJPY=X", True),
    ("AUD", "AUDUSD=X", False),
    ("NZD", "NZDUSD=X", False),
    ("CAD", "USDCAD=X", True),
    ("CHF", "USDCHF=X", True),
    ("SEK", "USDSEK=X", True),
    ("NOK", "USDNOK=X", True),
]

# 推荐交叉对的技术位置追踪
COMMON_PAIRS = {
    "EUR/USD":  "EURUSD=X",
    "GBP/USD":  "GBPUSD=X",
    "USD/JPY":  "USDJPY=X",
    "AUD/USD":  "AUDUSD=X",
    "USD/CAD":  "USDCAD=X",
    "USD/CHF":  "USDCHF=X",
    "NZD/USD":  "NZDUSD=X",
    "AUD/CAD":  "AUDCAD=X",
    "AUD/JPY":  "AUDJPY=X",
    "EUR/JPY":  "EURJPY=X",
    "GBP/JPY":  "GBPJPY=X",
    "EUR/GBP":  "EURGBP=X",
    "CAD/JPY":  "CADJPY=X",
    "CHF/JPY":  "CHFJPY=X",
    "AUD/NZD":  "AUDNZD=X",
    "NZD/CAD":  "NZDCAD=X",
}


def _safe_yf_download(ticker, **kwargs):
    """安全下载,出错返回 None"""
    if not YF_AVAILABLE:
        return None
    try:
        data = yf.download(ticker, progress=False, auto_adjust=True, **kwargs)
        if data is None or len(data) == 0:
            return None
        # yfinance 有时返回 MultiIndex 列,统一处理
        if hasattr(data.columns, "nlevels") and data.columns.nlevels > 1:
            data.columns = data.columns.get_level_values(0)
        return data
    except Exception as e:
        print(f"  yf 下载 {ticker} 失败: {e}")
        return None


def fetch_market_state() -> dict:
    """抓取市场状态快照(DXY/VIX/油/美债/金/股指)"""
    snapshot = {}
    for key, (ticker, label) in MARKET_TICKERS.items():
        data = _safe_yf_download(ticker, period="5d", interval="1d")
        if data is None or len(data) < 2:
            continue
        try:
            latest = float(data["Close"].iloc[-1])
            prev = float(data["Close"].iloc[-2])
            change_pct = (latest - prev) / prev * 100 if prev != 0 else 0
            snapshot[key] = {
                "label": label,
                "value": latest,
                "change_pct": change_pct,
            }
        except Exception as e:
            print(f"  解析 {key} 数据出错: {e}")
            continue
    return snapshot


def fetch_g10_moves() -> dict:
    """抓取 G10 各货币兑美元 24h 涨跌幅(%)
    返回 dict: {currency: pct_change_vs_usd}
    正值 = 该货币兑美元升值
    """
    moves = {}
    for ccy, ticker, inverted in G10_PAIRS:
        data = _safe_yf_download(ticker, period="3d", interval="1h")
        if data is None or len(data) < 24:
            # 退化使用日线数据
            data = _safe_yf_download(ticker, period="5d", interval="1d")
            if data is None or len(data) < 2:
                continue
            try:
                latest = float(data["Close"].iloc[-1])
                prev = float(data["Close"].iloc[-2])
            except Exception:
                continue
        else:
            try:
                latest = float(data["Close"].iloc[-1])
                prev = float(data["Close"].iloc[-24])
            except Exception:
                continue

        if prev == 0:
            continue
        raw_change = (latest - prev) / prev * 100
        # 如果 ticker 是 USD/XXX,涨意味着 XXX 贬值,需要取反
        moves[ccy] = -raw_change if inverted else raw_change

    # USD 的强弱用 DXY 衡量
    dxy_data = _safe_yf_download("DX-Y.NYB", period="3d", interval="1h")
    if dxy_data is not None and len(dxy_data) >= 24:
        try:
            latest = float(dxy_data["Close"].iloc[-1])
            prev = float(dxy_data["Close"].iloc[-24])
            if prev != 0:
                moves["USD"] = (latest - prev) / prev * 100
        except Exception:
            pass

    return moves


def fetch_technical_levels(pair_label: str) -> dict:
    """抓取某个货币对的技术位置数据"""
    ticker = COMMON_PAIRS.get(pair_label)
    if not ticker:
        return {}

    data = _safe_yf_download(ticker, period="60d", interval="1d")
    if data is None or len(data) < 20:
        return {}

    try:
        latest_close = float(data["Close"].iloc[-1])
        last_20 = data.tail(20)
        last_50 = data.tail(50) if len(data) >= 50 else data

        high_20d = float(last_20["High"].max())
        low_20d = float(last_20["Low"].min())
        sma_20 = float(last_20["Close"].mean())
        sma_50 = float(last_50["Close"].mean())

        # 经典枢轴点(基于昨日 OHLC)
        prev_high = float(data["High"].iloc[-2])
        prev_low = float(data["Low"].iloc[-2])
        prev_close = float(data["Close"].iloc[-2])
        pivot = (prev_high + prev_low + prev_close) / 3
        r1 = 2 * pivot - prev_low
        s1 = 2 * pivot - prev_high
        r2 = pivot + (prev_high - prev_low)
        s2 = pivot - (prev_high - prev_low)

        return {
            "pair": pair_label,
            "latest": latest_close,
            "high_20d": high_20d,
            "low_20d": low_20d,
            "sma_20": sma_20,
            "sma_50": sma_50,
            "pivot": pivot,
            "r1": r1, "s1": s1,
            "r2": r2, "s2": s2,
        }
    except Exception as e:
        print(f"  技术位置计算出错 {pair_label}: {e}")
        return {}


def fetch_all_pair_levels() -> dict:
    """批量抓所有常见对子的技术位置(给 LLM 选择用)"""
    levels = {}
    for pair_label in COMMON_PAIRS:
        lv = fetch_technical_levels(pair_label)
        if lv:
            levels[pair_label] = lv
    return levels


if __name__ == "__main__":
    print("=== 市场状态 ===")
    state = fetch_market_state()
    for k, v in state.items():
        print(f"  {v['label']}: {v['value']:.4f} ({v['change_pct']:+.2f}%)")

    print("\n=== G10 24h 涨跌(vs USD) ===")
    moves = fetch_g10_moves()
    for ccy, pct in sorted(moves.items(), key=lambda x: -x[1]):
        print(f"  {ccy}: {pct:+.2f}%")

    print("\n=== AUD/CAD 技术位置 ===")
    lv = fetch_technical_levels("AUD/CAD")
    for k, v in lv.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.4f}")
        else:
            print(f"  {k}: {v}")
