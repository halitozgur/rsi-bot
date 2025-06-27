import requests
import ccxt
import pandas as pd
import ta
import time
from config import BOT_TOKEN, CHAT_ID

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, data=data)

def fetch_ohlcv(symbol, timeframe='1h', limit=100):
    try:
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        return df
    except:
        return None

def detect_rsi_divergence(df, lookback=5):
    if df is None or len(df) < lookback + 2:
        return None

    rsi = ta.momentum.RSIIndicator(close=df['close'], window=14)
    df['rsi'] = rsi.rsi()
    recent_lows = df['low'].iloc[-lookback:]
    recent_rsi = df['rsi'].iloc[-lookback:]

    if recent_lows.iloc[-1] < recent_lows.iloc[0] and recent_rsi.iloc[-1] > recent_rsi.iloc[0]:
        return "🔄 Pozitif RSI Uyumsuzluğu"

    recent_highs = df['high'].iloc[-lookback:]
    if recent_highs.iloc[-1] > recent_highs.iloc[0] and recent_rsi.iloc[-1] < recent_rsi.iloc[0]:
        return "🔻 Negatif RSI Uyumsuzluğu"

    return None

def check_signal(df):
    if df is None or df.empty: return None

    ema = ta.trend.EMAIndicator(close=df['close'], window=200)
    df['ema200'] = ema.ema_indicator()

    atr = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close'], window=10)
    df['supertrend'] = df['close'] - 3 * atr.average_true_range()

    macd = ta.trend.macd_diff(df['close'])
    df['macd_hist'] = macd

    rsi = ta.momentum.RSIIndicator(close=df['close'], window=14)
    df['rsi'] = rsi.rsi()

    latest = df.iloc[-1]
    previous = df.iloc[-2]

    macd_buy = previous['macd_hist'] < 0 and latest['macd_hist'] > 0
    macd_sell = previous['macd_hist'] > 0 and latest['macd_hist'] < 0

    message = None

    if latest['close'] > latest['ema200'] and previous['close'] < previous['supertrend'] and latest['close'] > latest['supertrend'] and macd_buy:
        message = "📈 AL Sinyali (MACD + EMA + Supertrend)"
    elif latest['close'] < latest['ema200'] and previous['close'] > previous['supertrend'] and latest['close'] < latest['supertrend'] and macd_sell:
        message = "📉 SAT Sinyali (MACD + EMA + Supertrend)"

    divergence = detect_rsi_divergence(df)
    if divergence:
        message = (message or "ℹ️ RSI Uyumsuzluk") + f" + {divergence}"

    return message

exchange = ccxt.binance()
symbols = [s for s in exchange.load_markets() if s.endswith("/USDT") and ':' not in s]

while True:
    print("Taramaya başlandı...")
    for symbol in symbols:
        df = fetch_ohlcv(symbol)
        signal = check_signal(df)
        if signal:
            msg = f"{symbol} - {signal}"
            print(msg)
            send_telegram_message(msg)
    print("✅ Taramalar tamamlandı. 1 saat bekleniyor...\n")
    time.sleep(3600)
