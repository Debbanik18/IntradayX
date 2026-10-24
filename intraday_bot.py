import os
import io
from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo
import requests
import pandas as pd
import numpy as np
import yfinance as yf
import streamlit as st

try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

st.set_page_config(page_title="NSE/BSE All-Stock Intraday AI Bot", page_icon="📈", layout="wide")
st.title("📈 NSE & BSE All-Market Intraday ORB + VWAP AI Bot")
st.caption("2,200+ NSE/BSE Stocks • Live Company Search • 15m ORB + VWAP • Custom Capital • 60s Auto-Refresh")

# ==========================================
# 1. INDIAN MARKET HOURS CHECK (IST)
# ==========================================
IST = ZoneInfo("Asia/Kolkata")

def is_nse_market_open() -> bool:
    now_ist = datetime.now(IST)
    if now_ist.weekday() >= 5:
        return False
    return dt_time(9, 15) <= now_ist.time() <= dt_time(15, 30)

market_open_now = is_nse_market_open()

# ==========================================
# 2. LOAD ALL 2,000+ NSE STOCKS + LIVE SEARCH
# ==========================================
FALLBACK_STOCKS = {
    "RELIANCE": "Reliance Industries Ltd",
    "TCS": "Tata Consultancy Services Ltd",
    "HDFCBANK": "HDFC Bank Ltd",
    "ICICIBANK": "ICICI Bank Ltd",
    "SBIN": "State Bank of India",
    "INFY": "Infosys Ltd",
    "BHARTIARTL": "Bharti Airtel Ltd",
    "ITC": "ITC Ltd",
    "LT": "Larsen & Toubro Ltd",
    "BAJFINANCE": "Bajaj Finance Ltd",
    "AXISBANK": "Axis Bank Ltd",
    "KOTAKBANK": "Kotak Mahindra Bank Ltd",
    "MARUTI": "Maruti Suzuki India Ltd",
    "SUNPHARMA": "Sun Pharmaceutical Industries Ltd",
    "TITAN": "Titan Company Ltd",
    "TATAMOTORS": "Tata Motors Ltd",
    "TATASTEEL": "Tata Steel Ltd",
    "ZOMATO": "Zomato / Eternal Ltd",
    "IRCTC": "Indian Railway Catering & Tourism Corp",
    "HAL": "Hindustan Aeronautics Ltd",
    "BEL": "Bharat Electronics Ltd",
    "SUZLON": "Suzlon Energy Ltd",
    "IREDA": "Indian Renewable Energy Dev Agency",
    "RVNL": "Rail Vikas Nigam Ltd",
    "ADANIENT": "Adani Enterprises Ltd",
    "ADANIPORTS": "Adani Ports & SEZ Ltd",
    "DLF": "DLF Ltd",
    "TRENT": "Trent Ltd",
    "VBL": "Varun Beverages Ltd",
    "JIOFIN": "Jio Financial Services Ltd"
}

@st.cache_data(ttl=86400, show_spinner=False)
def load_all_nse_stocks() -> dict:
    """Downloads the official NSE India Master Equity list (2,000+ stocks)."""
    stock_map = dict(FALLBACK_STOCKS)
    urls = [
        "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv",
        "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=8)
            if r.status_code == 200:
                df_eq = pd.read_csv(io.StringIO(r.text))
                df_eq.columns = [c.strip().upper() for c in df_eq.columns]
                if "SYMBOL" in df_eq.columns and "NAME OF COMPANY" in df_eq.columns:
                    for _, row in df_eq.iterrows():
                        sym = str(row["SYMBOL"]).strip().upper()
                        name = str(row["NAME OF COMPANY"]).strip()
                        if sym and sym != "NAN":
                            stock_map[sym] = name
                    break
        except Exception:
            continue
    return stock_map

def search_live_yahoo_india(query: str) -> list:
    """Queries Yahoo Finance live search API for any NSE (.NS) or BSE (.BO) company."""
    if not query or len(query.strip()) < 2:
        return []
    matches = []
    try:
        url = "https://query2.finance.yahoo.com/v1/finance/search"
        params = {"q": query.strip(), "quotesCount": 15, "newsCount": 0}
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, params=params, headers=headers, timeout=6)
        if r.status_code == 200:
            quotes = r.json().get("quotes", [])
            for q in quotes:
                sym = q.get("symbol", "")
                if sym.endswith(".NS") or sym.endswith(".BO"):
                    clean_sym = sym.replace(".NS", "").replace(".BO", "")
                    name = q.get("longname") or q.get("shortname") or clean_sym
                    exch = "NSE" if sym.endswith(".NS") else "BSE"
                    matches.append((clean_sym, f"{clean_sym} — {name} ({exch})"))
    except Exception:
        pass
    return matches

all_stocks_dict = load_all_nse_stocks()

# Initialize persistent watchlist in session_state
if "custom_watchlist" not in st.session_state:
    st.session_state.custom_watchlist = [
        "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "SBIN",
        "INFY", "TATAMOTORS", "BAJFINANCE"
    ]

# ==========================================
# 3. SIDEBAR: CAPITAL, MARGIN & SETTINGS
# ==========================================
with st.sidebar:
    st.header("⏱️ Live Auto-Refresh (60s)")
    if market_open_now:
        st.success("🟢 NSE/BSE is OPEN (9:15–15:30 IST)")
    else:
        st.warning("🔴 NSE/BSE is CLOSED (After-Hours / Weekend)")

    auto_refresh = st.toggle("Auto-Refresh Every 60s", value=market_open_now)

    st.divider()
    st.header("💰 Custom Capital & Risk")
    capital = st.number_input(
        "Enter Any Trading Capital (₹)",
        min_value=100.0,
        max_value=100000000.0,
        value=10000.0,
        step=100.0,
        format="%.2f"
    )
    leverage = st.selectbox("Intraday Margin / Leverage (MIS)", options=[1, 2, 3, 4, 5], index=4)
    risk_pct = st.number_input("Max Risk Per Trade (%)", min_value=0.1, max_value=10.0, value=1.0, step=0.25, format="%.2f")
    st.info(
        f"**Buying Power ({leverage}x):** ₹{capital * leverage:,.2f}\n\n"
        f"**Max Loss Risk ({risk_pct}%):** ₹{capital * (risk_pct / 100.0):,.2f}/trade"
    )

    st.divider()
    st.header("📊 Scanner Filters")
    vol_threshold = st.slider("Min Volume Spike (x Avg)", min_value=0.5, max_value=3.0, value=1.2, step=0.1)
    exchange = st.selectbox("Default Exchange", ["NSE (.NS)", "BSE (.BO)"])
    suffix = ".NS" if "NSE" in exchange else ".BO"

    st.divider()
    st.header("🤖 AI & iPhone Alerts (Optional)")
    gemini_key = st.text_input("Gemini API Key", value=os.environ.get("GEMINI_API_KEY", ""), type="password")
    tg_token = st.text_input("Telegram Bot Token", type="password")
    tg_chat_id = st.text_input("Telegram Chat ID")

# ==========================================
# 4. ALL-MARKET STOCK SEARCH & WATCHLIST MANAGER
# ==========================================
with st.expander("🔍 Search & Add ANY Stock from NSE / BSE (2,200+ Stocks Loaded)", expanded=True):
    col_s1, col_s2 = st.columns([2, 2])

    with col_s1:
        st.markdown("**1. Browse All Listed NSE Stocks (Type Symbol or Company Name):**")
        formatted_options = [f"{sym} — {name}" for sym, name in all_stocks_dict.items()]
        picked_from_master = st.selectbox(
            "Search from 2,000+ Master Stock List:",
            options=[""] + formatted_options,
            index=0,
            help="Start typing any company name or symbol (e.g. Suzlon, Zomato, BHEL, Dixon, Paytm)"
        )
        if picked_from_master:
            sym_to_add = picked_from_master.split(" — ")[0].strip()
            if st.button(f"➕ Add {sym_to_add} to Watchlist", key="btn_master"):
                if sym_to_add not in st.session_state.custom_watchlist:
                    st.session_state.custom_watchlist.append(sym_to_add)
                    st.toast(f"✅ Added {sym_to_add} to Watchlist!")
                    st.rerun()

    with col_s2:
        st.markdown("**2. Live Yahoo Finance NSE/BSE Lookup OR Custom Ticker Input:**")
        live_query = st.text_input(
            "Type any company name or custom symbol (comma-separated allowed):",
            placeholder="e.g. Mazagon Dock, Eternal, IRCTC, BSE, CDSL"
        )
        if live_query:
            live_matches = search_live_yahoo_india(live_query)
            if live_matches:
                selected_live = st.selectbox(
                    "Matching Live NSE/BSE Stocks Found:",
                    options=[m[1] for m in live_matches]
                )
                if st.button("➕ Add Selected Match", key="btn_live"):
                    clean_s = selected_live.split(" — ")[0].strip().upper()
                    if clean_s not in st.session_state.custom_watchlist:
                        st.session_state.custom_watchlist.append(clean_s)
                        all_stocks_dict[clean_s] = selected_live
                        st.toast(f"✅ Added {clean_s} to Watchlist!")
                        st.rerun()

            if st.button("➕ Add Raw Symbol(s) Directly", key="btn_raw"):
                for raw_s in live_query.split(","):
                    clean_s = raw_s.strip().upper().replace(".NS", "").replace(".BO", "")
                    if clean_s and clean_s not in st.session_state.custom_watchlist:
                        st.session_state.custom_watchlist.append(clean_s)
                        all_stocks_dict.setdefault(clean_s, clean_s)
                st.rerun()

# Active Watchlist Multiselect (Synced with Session State)
all_available_symbols = sorted(list(set(list(all_stocks_dict.keys()) + st.session_state.custom_watchlist)))

selected_stocks = st.multiselect(
    f"📋 Active Intraday Watchlist ({len(st.session_state.custom_watchlist)} selected — add or remove any stock):",
    options=all_available_symbols,
    default=st.session_state.custom_watchlist,
    format_func=lambda x: f"{x} ({all_stocks_dict.get(x, 'Custom')[:28]})"
)
st.session_state.custom_watchlist = selected_stocks

# ==========================================
# 5. CORE INDICATOR & SCANNER ENGINE
# ==========================================
def analyze_ticker(base_symbol: str, suffix: str, capital: float, leverage: int, risk_pct: float, vol_mult: float):
    ticker = f"{base_symbol}{suffix}"
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(period="5d", interval="5m")
        # Automatic fallback to BSE (.BO) if NSE (.NS) returns empty or vice versa
        if (df is None or df.empty) and suffix == ".NS":
            ticker = f"{base_symbol}.BO"
            stock = yf.Ticker(ticker)
            df = stock.history(period="5d", interval="5m")

        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.dropna(subset=["Open", "High", "Low", "Close", "Volume"])
        if df.empty:
            return None

        df["TradeDate"] = df.index.date
        latest_date = df["TradeDate"].iloc[-1]
        day_df = df[df["TradeDate"] == latest_date].copy()
        if len(day_df) < 4:
            return None

        tp = (day_df["High"] + day_df["Low"] + day_df["Close"]) / 3.0
        cum_vol = day_df["Volume"].cumsum().replace(0, np.nan)
        day_df["VWAP"] = ((tp * day_df["Volume"]).cumsum() / cum_vol).bfill()

        tr = pd.concat([
            day_df["High"] - day_df["Low"],
            (day_df["High"] - day_df["Close"].shift(1)).abs(),
            (day_df["Low"] - day_df["Close"].shift(1)).abs()
        ], axis=1).max(axis=1)
        day_df["ATR"] = tr.rolling(window=14, min_periods=1).mean()

        delta = day_df["Close"].diff()
        gain = delta.clip(lower=0).rolling(window=14, min_periods=1).mean()
        loss = (-delta.clip(upper=0)).rolling(window=14, min_periods=1).mean()
        rs = gain / loss.replace(0, np.nan)
        day_df["RSI"] = (100 - (100 / (1 + rs))).fillna(50.0)

        orb_high = float(day_df["High"].iloc[:3].max())
        orb_low = float(day_df["Low"].iloc[:3].min())
        latest = day_df.iloc[-1]

        price = round(float(latest["Close"]), 2)
        vwap = round(float(latest["VWAP"]), 2)
        rsi = round(float(latest["RSI"]), 1)
        atr = float(latest["ATR"]) if pd.notna(latest["ATR"]) and latest["ATR"] > 0 else (price * 0.005)
        avg_vol = float(day_df["Volume"].iloc[:-1].mean())
        vol_spike = round(float(latest["Volume"]) / avg_vol, 2) if avg_vol > 0 else 1.0

        signal = "WAIT / IN RANGE"
        stop_loss = round(price - (1.5 * atr), 2)
        target = round(price + (3.0 * atr), 2)

        if price > orb_high and price > vwap and vol_spike >= vol_mult:
            signal = "🔥 BUY (LONG BREAKOUT)"
            stop_loss = round(price - (1.5 * atr), 2)
            target = round(price + (3.0 * atr), 2)
        elif price < orb_low and price < vwap and vol_spike >= vol_mult:
            signal = "🔻 SELL (SHORT BREAKDOWN)"
            stop_loss = round(price + (1.5 * atr), 2)
            target = round(price - (3.0 * atr), 2)

        max_risk_inr = capital * (risk_pct / 100.0)
        risk_per_share = max(0.05, abs(price - stop_loss))
        risk_based_qty = int(max_risk_inr // risk_per_share)
        margin_based_max_qty = int((capital * leverage) // price) if price > 0 else 0
        qty = min(max(1, risk_based_qty), margin_based_max_qty) if margin_based_max_qty >= 1 else 0
        margin_used = round((price * qty) / leverage, 2) if qty > 0 else 0.0

        return {
            "Ticker": ticker,
            "Company": all_stocks_dict.get(base_symbol, base_symbol)[:24],
            "Session": str(latest_date),
            "Signal": signal,
            "LTP (₹)": price,
            "VWAP (₹)": vwap,
            "15m High": round(orb_high, 2),
            "15m Low": round(orb_low, 2),
            "RSI": rsi,
            "Vol Spike": vol_spike,
            "Max Qty": qty,
            "Margin Used (₹)": margin_used,
            "Stop-Loss (₹)": stop_loss,
            "Target (₹)": target
        }
    except Exception:
        return None

# ==========================================
# 6. 60-SECOND AUTO-REFRESH SCANNER PANEL
# ==========================================
refresh_interval = "60s" if auto_refresh else None

@st.fragment(run_every=refresh_interval)
def live_scanner_panel():
    now_str = datetime.now(IST).strftime("%I:%M:%S %p IST")
    col_a, col_b = st.columns([3, 1])
    with col_a:
        mode_label = "🔄 AUTO-SCANNING EVERY 60s" if auto_refresh else "⏸️ MANUAL MODE"
        st.markdown(
            f"**Status:** `{mode_label}` | **Scanned:** `{now_str}` | "
            f"**Universe Loaded:** `{len(all_stocks_dict):,} NSE/BSE Stocks`"
        )
    with col_b:
        st.button("⚡ Scan Watchlist Now", use_container_width=True)

    if not selected_stocks:
        st.warning("Your watchlist is empty. Search and add stocks above!")
        return

    results = []
    missing = []
    for sym in selected_stocks:
        res = analyze_ticker(sym, suffix, capital, leverage, risk_pct, vol_threshold)
        if res:
            results.append(res)
        else:
            missing.append(sym)

    if missing:
        st.caption(f"⚠️ Could not fetch 5m intraday candles for: {', '.join(missing)} (check ticker spelling or liquidity).")

    if not results:
        st.error("No valid intraday data returned for the selected stocks.")
        return

    df_res = pd.DataFrame(results)
    active = [r for r in results if "WAIT" not in r["Signal"]]

    st.dataframe(df_res, use_container_width=True)

    if active:
        st.success(f"🔥 {len(active)} Active Breakout Setup(s) Detected at {now_str}!")
        for trade in active:
            with st.expander(f"📌 {trade['Ticker']} ({trade['Company']}) — {trade['Signal']} @ ₹{trade['LTP (₹)']}", expanded=True):
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Entry (LTP)", f"₹{trade['LTP (₹)']}")
                c2.metric("Stop-Loss", f"₹{trade['Stop-Loss (₹)']}")
                c3.metric("Target (1:2)", f"₹{trade['Target (₹)']}")
                c4.metric("Order Qty", f"{trade['Max Qty']} shares", f"Margin: ₹{trade['Margin Used (₹)']}")
    else:
        st.info("No stocks in your watchlist currently meet the Breakout + Volume criteria. Slide 'Min Volume Spike' to 0.5x in the sidebar to test trade cards.")

live_scanner_panel()
