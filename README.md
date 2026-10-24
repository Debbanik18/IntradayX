# 📈 NSE & BSE Intraday AI Trading & Breakout Bot

A real-time intraday stock screener, technical indicator calculator, and AI risk-management assistant built with **Python**, **Streamlit**, and **Google Gemini**. Designed specifically for Indian stock markets (**NSE and BSE**).

---

## ✨ Key Features

* **2,200+ Stock Search & Watchlist:** Automatically pulls the official NSE master equity list and provides live Yahoo Finance search lookup to add any stock instantly.
* **15-Min Opening Range Breakout (ORB) + VWAP Filter:** Scans 5-minute candles to detect institutional breakouts while filtering out fakeouts using Volume Spikes and VWAP alignment.
* **Custom Capital & MIS Leverage Calculator:** Set any exact rupee trading capital and 1x–5x intraday leverage to automatically calculate safe position sizes.
* **Strict 1% Risk Position Sizing:** Computes exact share quantities based on Average True Range (ATR) stop-losses.
* **Gemini AI Risk Manager:** Passes filtered breakouts and news headlines to Google Gemini (`gemini-2.5-flash`) for instant qualitative conviction scoring.
* **60s Auto-Refresh Dashboard:** Automatically re-scans the market every 60 seconds during NSE trading hours (9:15 AM – 3:30 PM IST).
* **Cross-Platform & Mobile Ready:** Run locally on macOS/Windows or deploy for free on Streamlit Cloud to view on iPhones and Android devices.

---

## 🛠️ Tech Stack

* **Frontend & UI:** Streamlit
* **Market Data & News:** `yfinance`, Requests
* **Math & Indicators:** Pandas, NumPy
* **AI Analysis:** Google GenAI SDK (`google-genai`)

---

## 🚀 Quick Start (Local Installation)

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/Debbanik18/nse-bse-intraday-bot.git](https://github.com/Debbanik18/nse-bse-intraday-bot.git)
   cd nse-bse-intraday-bot
   python3 -m venv venv
1) source venv/bin/activate  # On Windows use: venv\Scripts\activate
2) pip install -r requirements.txt
3) streamlit run intraday_bot.py
