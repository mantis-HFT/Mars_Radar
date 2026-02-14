import os
import sys
import configparser
import warnings
import numpy as np
import pandas as pd
import sqlite3
import datetime
import time
import requests
import logging
import ccxt
import random
from concurrent.futures import ThreadPoolExecutor
from tabulate import tabulate
from collections import Counter
from tqdm import tqdm

# --- 1. SUPPRESS ALL WARNINGS ---
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 
os.environ['PYTHONWARNINGS'] = 'ignore'
from statsmodels.tools.sm_exceptions import ValueWarning
warnings.filterwarnings("ignore")
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)
warnings.simplefilter(action='ignore', category=RuntimeWarning)
warnings.simplefilter(action='ignore', category=ValueWarning)
pd.options.mode.chained_assignment = None
if not hasattr(np, 'NaN'): np.NaN = np.nan

# Moved pandas_ta import here
import pandas_ta as ta

# IMPORT PDRS MODULE
try:
    import pdrs_calculator
    PDRS_AVAILABLE = True
except ImportError:
    print("⚠️ Could not import pdrs_calculator.py. PDRS features will be disabled.")
    PDRS_AVAILABLE = False

# --- AI Libraries ---
import tensorflow as tf
tf.get_logger().setLevel(logging.ERROR)
from statsmodels.tsa.statespace.sarimax import SARIMAX
from lightgbm import LGBMRegressor
import keras
from keras import Sequential
from keras.layers import LSTM, Dense, Input
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error

# --- CONFIGURATION ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, 'config.ini')
DB_NAME = os.path.join(SCRIPT_DIR, "market_data_radar_n.db")

config = configparser.ConfigParser()
if os.path.exists(CONFIG_FILE):
    config.read(CONFIG_FILE)
else:
    pass

# Default values
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_IDS = []
CHECK_INTERVAL_SECONDS = 3600
TOP_N_COINS = 30
GRID_TARGET_DAYS = 3.0
GRID_WIDTH_FACTOR = 2.0
MIN_PROFIT_PER_GRID = 0.002
ATR_FACTOR = 1.0
FIB_LOOKBACK_DAYS = 3.0
STD_MIN_VOL = 15000000
SPIKE_MIN_VOL = 2000000
VOL_SPIKE_RATIO = 3.0
CRAZY_DAY_THRESHOLD = 3.0

try:
    if os.path.exists(CONFIG_FILE):
        radar_conf = config['radar_settings']
        TELEGRAM_BOT_TOKEN = radar_conf.get('telegram_bot_token', '')
        TELEGRAM_CHAT_IDS = [x.strip() for x in radar_conf.get('telegram_chat_ids', '').split(',') if x.strip()]
        CHECK_INTERVAL_SECONDS = int(radar_conf.get('check_interval_seconds', 3600))
        TOP_N_COINS = int(radar_conf.get('top_n_coins', 30))
        GRID_TARGET_DAYS = float(radar_conf.get('grid_target_days', 3.0))
        GRID_WIDTH_FACTOR = float(radar_conf.get('grid_width_factor', 2.0))
        MIN_PROFIT_PER_GRID = float(radar_conf.get('min_profit_per_grid', 0.002))
        ATR_FACTOR = float(radar_conf.get('atr_factor', 1.0))
        FIB_LOOKBACK_DAYS = float(radar_conf.get('fib_lookback_days', 3.0))
        
        STD_MIN_VOL = float(radar_conf.get('standard_min_volume', 15000000))
        SPIKE_MIN_VOL = float(radar_conf.get('spike_min_volume', 2000000))
        VOL_SPIKE_RATIO = float(radar_conf.get('volume_spike_ratio', 3.0))
        CRAZY_DAY_THRESHOLD = float(radar_conf.get('crazy_day_threshold', 3.0))
except Exception as e:
    print(f"⚠️ Config Load Error (Using Defaults): {e}")

# FORCE UTF-8 LOGGING
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [MARS V10] - %(message)s',
    handlers=[
        logging.FileHandler("mars_radar.log", encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# --- EXCHANGE INITIALIZATION ---
try:
    binance = ccxt.binance({
        'options': {'defaultType': 'future'}, 
        'enableRateLimit': True,
        'timeout': 10000
    })
    bybit = ccxt.bybit({
        'options': {'defaultType': 'future'}, 
        'enableRateLimit': True,
        'timeout': 10000
    })
except Exception as e:
    logging.error(f"Exchange Init Error: {e}")
    sys.exit(1)

# --- DATABASE ---
def init_db():
    try:
        conn = sqlite3.connect(DB_NAME, timeout=60)
        cursor = conn.cursor()
        cursor.execute('PRAGMA journal_mode=WAL;')
        cursor.execute('''CREATE TABLE IF NOT EXISTS market_data (ticker TEXT, interval TEXT, timestamp DATETIME, open REAL, high REAL, low REAL, close REAL, volume REAL, PRIMARY KEY (ticker, interval, timestamp))''')
        conn.commit()
        conn.close()
        logging.info(f"Database initialized at {DB_NAME} (WAL Mode)")
    except Exception as e:
        logging.error(f"DB Init Error: {e}")

def get_interval_ms(interval):
    if interval == '1m': return 60 * 1000
    if interval == '5m': return 5 * 60 * 1000
    if interval == '1h': return 60 * 60 * 1000
    if interval == '1d': return 24 * 60 * 60 * 1000
    return 60 * 1000

# --- DATA FETCHING (SAFE MODE) ---
def fetch_funding_data_safe(ticker):
    try:
        data = bybit.fetch_funding_rate(ticker)
        return {
            'rate': data.get('fundingRate', 0.0),
            'nextTime': data.get('fundingTimestamp')
        }
    except:
        try:
            data = binance.fetch_funding_rate(ticker)
            return {
                'rate': data.get('fundingRate', 0.0),
                'nextTime': data.get('fundingTimestamp')
            }
        except:
            return {'rate': 0.0, 'nextTime': None}

def fetch_ohlcv_redundant(ticker, interval, since, limit):
    time.sleep(random.uniform(0.1, 0.5))
    try:
        return bybit.fetch_ohlcv(ticker, interval, since=since, limit=limit)
    except (ccxt.RateLimitExceeded, ccxt.NetworkError) as e:
        pass
    except Exception: 
        pass
    
    try:
        return binance.fetch_ohlcv(ticker, interval, since=since, limit=limit)
    except Exception: return []

def fetch_candles_logic(ticker, interval, lookback_limit=1000):
    try:
        conn = sqlite3.connect(DB_NAME, timeout=10, uri=True) 
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(timestamp) FROM market_data WHERE ticker=? AND interval=?", (ticker, interval))
        res = cursor.fetchone()
        conn.close()
        last_ts_str = res[0] if res else None
        now_ms = int(time.time() * 1000)
        interval_ms = get_interval_ms(interval)
        since = None
        if last_ts_str:
            try:
                last_ts_dt = pd.to_datetime(last_ts_str)
                since = int(last_ts_dt.timestamp() * 1000) + interval_ms
            except: since = None
        if not since: since = now_ms - (lookback_limit * interval_ms)
        new_candles = []
        if since < now_ms:
            ohlcv = fetch_ohlcv_redundant(ticker, interval, since, 1000)
            if ohlcv: new_candles.extend(ohlcv)
        data_tuples = []
        if new_candles:
            for c in new_candles:
                ts_str = pd.to_datetime(c[0], unit='ms').strftime('%Y-%m-%d %H:%M:%S')
                data_tuples.append((ticker, interval, ts_str, c[1], c[2], c[3], c[4], c[5]))
        return data_tuples
    except Exception: return []

def save_batch_to_db(all_data_tuples):
    if not all_data_tuples: return
    try:
        conn = sqlite3.connect(DB_NAME, timeout=120)
        cursor = conn.cursor()
        cursor.executemany('INSERT OR IGNORE INTO market_data VALUES (?, ?, ?, ?, ?, ?, ?, ?)', all_data_tuples)
        conn.commit()
        conn.close()
        logging.info(f"Saved {len(all_data_tuples)} new records to DB.")
    except Exception as e:
        logging.error(f"Batch Save Error: {e}")

def load_data_from_db(ticker, interval, limit=500):
    try:
        conn = sqlite3.connect(DB_NAME, timeout=30)
        query = f"SELECT timestamp, open, high, low, close, volume FROM market_data WHERE ticker='{ticker}' AND interval='{interval}' ORDER BY timestamp DESC LIMIT {limit}"
        df = pd.read_sql_query(query, conn)
        conn.close()
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            df.sort_index(inplace=True)
            return df
    except Exception: pass
    return pd.DataFrame()

# --- UTILS ---
def send_telegram_alert(header, body_lines):
    if not body_lines: return

    MAX_LEN = 3800
    current_chunk = header + "\n\n"
    chunks = []
    
    for line in body_lines:
        if len(current_chunk) + len(line) > MAX_LEN:
            chunks.append(current_chunk)
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            current_chunk = f"Mars Radar V10 (Part 2)\nScan Time: {timestamp} (cont)\n\n" + line
        else:
            current_chunk += line

    if current_chunk:
        chunks.append(current_chunk)
    
    for chunk in chunks:
        for chat_id in TELEGRAM_CHAT_IDS:
            try:
                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                requests.post(url, data={'chat_id': chat_id, 'text': chunk, 'parse_mode': 'HTML'}, timeout=10)
                time.sleep(0.5) 
            except Exception as e:
                 logging.error(f"Telegram Error: {str(e)}")

def smart_format(value):
    if value is None or np.isnan(value): return "0"
    if value > 1000: return f"{value:.0f}"
    elif value < 0.001: return f"{value:.7f}"
    elif value < 1: return f"{value:.5f}"
    else: return f"{value:.4f}"

def get_initial_tickers():
    valid = []
    try:
        tickers = bybit.fetch_tickers()
        logging.info(f"Bybit found {len(tickers)} raw tickers.")
        for s, d in tickers.items():
            if s.endswith('USDT'): 
                vol = d.get('quoteVolume')
                if vol is None: 
                    base_vol = d.get('baseVolume')
                    close_px = d.get('close')
                    if base_vol and close_px: vol = base_vol * close_px
                    else: vol = 0
                if vol > SPIKE_MIN_VOL:
                    valid.append({'symbol': s, 'vol': vol})
        logging.info(f"Bybit filtered: {len(valid)} valid candidates.")
    except Exception as e:
        logging.warning(f"Bybit Blocked/Error: {e}. Switching to Binance...")

    if len(valid) < 10:
        try:
            tickers = binance.fetch_tickers()
            logging.info(f"Binance found {len(tickers)} raw tickers.")
            for s, d in tickers.items():
                if s.endswith('USDT'):
                    vol = d.get('quoteVolume')
                    if vol is None: 
                        base_vol = d.get('baseVolume')
                        close_px = d.get('close')
                        if base_vol and close_px: vol = base_vol * close_px
                        else: vol = 0
                    if vol > SPIKE_MIN_VOL:
                        if not any(v['symbol'] == s for v in valid):
                            valid.append({'symbol': s, 'vol': vol})
            logging.info(f"After Binance check: {len(valid)} valid candidates.")
        except Exception as e:
            logging.error(f"Binance Ticker Fetch Failed: {e}")

    if not valid:
        logging.error("CRITICAL: No tickers found from any exchange.")
        return []

    sorted_list = sorted(valid, key=lambda x: x['vol'], reverse=True)
    final_list = [x['symbol'] for x in sorted_list[:TOP_N_COINS * 5]]
    logging.info(f"Selected top {len(final_list)} tickers for scanning.")
    return final_list

# --- RISK ANALYSIS: CRAZY EVENTS ---
def analyze_crazy_event(ticker, event_date, df_1h):
    try:
        start_date = pd.to_datetime(event_date) - pd.Timedelta(days=1)
        end_date = pd.to_datetime(event_date) + pd.Timedelta(days=5)
        
        mask = (df_1h.index >= start_date) & (df_1h.index <= end_date)
        window = df_1h.loc[mask]
        
        if window.empty: return None
        
        low_price = window['low'].min()
        high_price = window['high'].max()
        peak_idx = window['high'].idxmax()
        pump_pct = (high_price - low_price) / low_price * 100
        
        fib_0618 = high_price - (high_price - low_price) * 0.618
        
        post_peak = window.loc[peak_idx:]
        dump_below_fib = False
        
        if not post_peak.empty:
             dump_mask = post_peak['low'] < fib_0618
             if dump_mask.any():
                 dump_below_fib = True
        
        pre_event_mask = df_1h.index < start_date
        avg_vol_pre = df_1h.loc[pre_event_mask]['volume'].tail(24).mean()
        peak_vol = window['volume'].max()
        vol_surge = peak_vol / avg_vol_pre if avg_vol_pre > 0 else 0
        
        return {
            'date': event_date, 'pump_pct': pump_pct,
            'low': low_price, 'high': high_price,
            'vol_surge': vol_surge, 'fib_broken': dump_below_fib,
            'is_detailed': True
        }
    except: return None

def analyze_crazy_daily_context(ticker, event_date, df_1d, current_price):
    try:
        if event_date not in df_1d.index:
            try: loc_idx = df_1d.index.get_loc(event_date)
            except: return None
        else:
             loc_idx = df_1d.index.get_loc(event_date)
             
        event_row = df_1d.iloc[loc_idx]
        pump_high = event_row['high']
        pump_low = event_row['low']
        pump_open = event_row['open']
        pump_vol = event_row['volume']
        pump_pct = (pump_high - pump_low) / pump_low * 100
        pump_range = pump_high - pump_low
        if pump_range == 0: pump_range = 0.000001
        
        fib_618_price = pump_high - (pump_range * 0.618)
        fib_786_price = pump_high - (pump_range * 0.786)
        
        # --- PRE-EVENT ANALYSIS ---
        pre_dump_msg = ""
        is_dump_first = False
        
        if loc_idx > 0:
            prev_day = df_1d.iloc[loc_idx - 1]
            prev_close = prev_day['close']
            drop_from_prev = (pump_low - prev_close) / prev_close * 100
            
            if drop_from_prev < -10.0:
                is_dump_first = True
                pre_dump_msg = f"Flash Crash ({drop_from_prev:.0f}%) then Pump"
            elif pump_open < prev_close * 0.95:
                 pre_dump_msg = "Gap Down then Pump"
        
        look_ahead_days = 30
        scan_window = df_1d.iloc[loc_idx+1 : loc_idx+1+look_ahead_days]
        
        retest_found = False
        retest_date_str = ""
        aftermath_msg = ""
        result_msg = ""
        
        retest_idx = -1
        days_later = 0
        
        for i in range(len(scan_window)):
            day = scan_window.iloc[i]
            if day['low'] <= fib_618_price:
                retest_found = True
                retest_idx = i
                days_later = i + 1
                retest_date_str = scan_window.index[i].strftime('%m-%d')
                break
        
        analysis_lines = []
        pump_x = pump_high / pump_low
        
        if is_dump_first:
             analysis_lines.append(f"Structure: {pre_dump_msg}. (High Risk)")
             analysis_lines.append(f"Recovery x{pump_x:.1f} ({pump_pct:.0f}%): Strong Buy-the-dip Signal.")
        elif pump_pct > 500:
            analysis_lines.append(f"Pump x{pump_x:.1f} ({pump_pct:.0f}%): Fake Pump / Bull Trap.")
        elif pump_pct > 200:
            analysis_lines.append(f"Pump x{pump_x:.1f} ({pump_pct:.0f}%): Extreme Pump (FOMO).")
        else:
            analysis_lines.append(f"Pump x{pump_x:.1f} ({pump_pct:.0f}%): Standard High Volatility.")

        if retest_found:
            retest_day_row = scan_window.iloc[retest_idx]
            retest_date_abs = scan_window.index[retest_idx]
            outcome_window = df_1d.loc[retest_date_abs:].iloc[1:6]
            aftermath_msg = f"📉 Retest: Hit Fib 61.8% on {retest_date_str} (+{days_later}d)"
            
            if days_later <= 2:
                analysis_lines.append(f"Retest +{days_later}d: Freefall: Immediate rejection at Fib 61.8%.")
            elif days_later > 10:
                analysis_lines.append(f"Retest +{days_later}d: Sustained high before correction.")
            else:
                analysis_lines.append(f"Retest +{days_later}d: Standard correction.")

            if not outcome_window.empty:
                max_bounce = outcome_window['high'].max()
                min_dump = outcome_window['low'].min()
                bounce_pct = (max_bounce - retest_day_row['low']) / retest_day_row['low'] * 100
                deep_dump = min_dump <= fib_786_price
                
                if deep_dump:
                    result_msg = f"❌ Crashed to Fib 78.6%"
                    analysis_lines.append("Crashed: Support Collapsed (Structure Broken).")
                    conclusion = "👉 CONCLUSION: Do not Long. Market structure broken."
                elif bounce_pct > 15:
                    result_msg = f"🟢 Bounced +{bounce_pct:.0f}%"
                    analysis_lines.append(f"Bounced: Strong buying pressure (+{bounce_pct:.0f}%).")
                    conclusion = "👉 CONCLUSION: Good elasticity. Suitable for Neutral Grid."
                else:
                    result_msg = f"⚠️ Weak Hover ({bounce_pct:.0f}%)"
                    analysis_lines.append("Weak: Weak Hover: No demand at support.")
                    conclusion = "👉 CONCLUSION: Weak buying. Risk of lower lows remains."
            else:
                result_msg = "Running... (Retest just happened)"
                conclusion = "👉 CONCLUSION: Critical phase."
        else:
            aftermath_msg = f"🔥 Super Strong: Never retested Fib 61.8%"
            analysis_lines.append("Strong Hold: Did not retest Fib 61.8%.")
            max_post_high = scan_window['high'].max()
            
            # --- FIX: Handle empty/recent window for 'Today's event' ---
            if pd.isna(max_post_high) or max_post_high is None:
                max_post_high = pump_high # Assume not broken yet if just happened
            
            if max_post_high > pump_high:
                result_msg = f"🚀 Continued Up (+{((max_post_high-pump_high)/pump_high)*100:.0f}%)"
                analysis_lines.append("Continuation: Breaking new highs.")
                conclusion = "👉 CONCLUSION: Trend too strong (FOMO). Shorting is dangerous."
            else:
                result_msg = "➡️ Consolidated High"
                analysis_lines.append("Consolidated: Sideways at peak.")
                conclusion = "👉 CONCLUSION: Holding value. Safe High."

        relative_pos = (current_price - pump_low) / pump_range
        grid_eval = ""
        
        if relative_pos < 0.3:
            if "Strong" in aftermath_msg or "Continued" in result_msg or "Consolidated" in result_msg:
                grid_eval = "⚠️ Trap Risk: Low Price + History of Holding Highs"
            elif "Crashed" in result_msg or "Retest" in aftermath_msg:
                grid_eval = "✅ Elastic: History of Returning to Base"
        elif relative_pos > 0.7:
            if "Strong" in aftermath_msg or "Consolidated" in result_msg:
                grid_eval = "✅ Safe High: History of Support"
            elif "Crashed" in result_msg:
                grid_eval = "⚠️ Dump Risk: History of Failing at Top"
        else:
             grid_eval = "ℹ️ Mid-Range Context"

        # --- CHANGED: Format Date to String ---
        formatted_date = event_date.strftime('%Y-%m-%d') if hasattr(event_date, 'strftime') else str(event_date)

        return {
            'date': formatted_date, 'pump_pct': pump_pct,
            'low': pump_low, 'high': pump_high,
            'vol_surge': -1, 'fib_broken': False,
            'aftermath': aftermath_msg,
            'result': result_msg,
            'grid_eval': grid_eval,
            'analysis_lines': analysis_lines,
            'conclusion': conclusion,
            'is_detailed': False # Forces Text Block
        }
    except Exception as e:
        return None

# --- METRICS & AI ---
def calculate_metrics_chunk(df):
    if df is None or len(df) < 5: return None, 0, 0, 0
    mean_price = df['close'].mean()
    counts, bins = np.histogram(df['close'], bins=20)
    mode_price = (bins[np.argmax(counts)] + bins[np.argmax(counts)+1]) / 2
    df['pct_change'] = df['close'].pct_change()
    direction = np.sign(df['pct_change'].fillna(0)).astype(int)
    y = direction.values
    max_streak = 0
    if len(y) > 0:
        change_points = np.diff(np.concatenate(([-999], y, [999]))) != 0
        indices = np.where(change_points)[0]
        valid_runs = np.diff(indices)[y[indices[:-1]] != 0]
        if len(valid_runs) > 0: max_streak = np.max(valid_runs)
    return df, mean_price, mode_price, max_streak

def process_macro_data(df):
    bb = ta.bbands(df['close'], length=24, std=2)
    df['BB_Width_Pct'] = ((bb['BBU_24_2.0'] - bb['BBL_24_2.0']) / df['close']) * 100
    df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)
    vol_24h = df['volume'].tail(24).mean()
    vol_7d = df['volume'].tail(168).mean()
    df['Vol_Trend'] = vol_24h / vol_7d if vol_7d > 0 else 1.0
    df['SMA_20'] = ta.sma(df['close'], length=20)
    recent = df.tail(48)
    crosses = len(recent[(recent['close'] > recent['SMA_20']) != (recent['close'].shift(1) > recent['SMA_20'].shift(1))])
    adx = ta.adx(df['high'], df['low'], df['close'], length=14)
    df['ADX'] = adx['ADX_14']
    df.dropna(inplace=True)
    return df, crosses, df['Vol_Trend'].iloc[-1]

def calculate_micro_atr(df_1m, df_5m):
    atr_val = 0
    if not df_5m.empty: atr_val += ta.atr(df_5m['high'], df_5m['low'], df_5m['close'], length=14).mean()
    if not df_1m.empty:
        atr_1m = ta.atr(df_1m['high'], df_1m['low'], df_1m['close'], length=14).mean()
        atr_val = (atr_val + atr_1m) / 2 if atr_val > 0 else atr_1m
    return atr_val

def run_ensemble_models(df):
    try:
        model_s = SARIMAX(df['close'], order=(1,1,1), enforce_stationarity=False, enforce_invertibility=False)
        fit_s = model_s.fit(disp=False)
        p_s = fit_s.get_forecast(steps=1).predicted_mean.iloc[-1]
    except: p_s = np.nan
    try:
        data = df.copy()
        for i in range(1, 4): data[f'lag_{i}'] = data['close'].shift(i)
        data.dropna(inplace=True)
        X = data.drop(columns=['close']); y = data['close']
        model_l = LGBMRegressor(n_estimators=50, verbose=-1).fit(X.iloc[:-1], y.iloc[:-1])
        p_l = model_l.predict(X.iloc[[-1]])[0]
    except: p_l = np.nan
    try:
        data_v = df['close'].values.reshape(-1, 1)
        scaler = MinMaxScaler(); scaled = scaler.fit_transform(data_v)
        X, y = [], []
        lb = 10
        for i in range(lb, len(scaled)): X.append(scaled[i-lb:i, 0]); y.append(scaled[i, 0])
        X, y = np.array(X), np.array(y); X = np.reshape(X, (X.shape[0], X.shape[1], 1))
        model_n = Sequential()
        model_n.add(Input(shape=(lb, 1))); model_n.add(LSTM(20, activation='relu')); model_n.add(Dense(1))
        model_n.compile(optimizer='adam', loss='mse')
        model_n.fit(X, y, epochs=3, verbose=0, batch_size=32)
        p_n_scaled = model_n.predict(scaled[-lb:].reshape(1, lb, 1), verbose=0)
        p_n = scaler.inverse_transform(p_n_scaled)[0][0]
    except: p_n = np.nan
    return p_s, p_l, p_n

# --- ANALYZER ---
def process_ticker_logic(ticker, df_1d, df_1h, df_5m, df_1m):
    try:
        if df_1h.empty or len(df_1h) < 50: 
            return {'status': 'Insufficient Data', 'ticker': ticker}

        current_price = df_1h['close'].iloc[-1]
        
        # --- FUNDING RATE CHECK ---
        funding_data = fetch_funding_data_safe(ticker)
        funding_rate = funding_data['rate']
        next_funding_time = funding_data['nextTime']
        
        funding_apr = abs(funding_rate) * 3 * 365 * 100 
        funding_warning = ""
        funding_penalty = 1.0
        
        if funding_apr > 100:
            funding_penalty = 0.5
            funding_warning = "⛔"
        elif funding_apr > 50:
            funding_penalty = 0.8
            funding_warning = "⚠️"
            
        time_str = ""
        if next_funding_time:
            now_ms = int(time.time() * 1000)
            delta = next_funding_time - now_ms
            if delta > 0:
                hours = int(delta / (1000 * 60 * 60))
                mins = int((delta / (1000 * 60)) % 60)
                time_str = f"(Next: {hours}h {mins}m)"
                if delta < 15 * 60 * 1000 and abs(funding_rate) > 0.0005:
                    funding_warning = "🚨 FEE SOON! " + funding_warning

        funding_str = f"{funding_warning}Fund: {funding_rate*100:.3f}% {time_str} | APR: {funding_apr:.0f}%"

        current_24h_vol = df_1h['volume'].tail(24).sum() * current_price
        vol_recent_avg = df_1h['volume'].tail(4).mean()
        vol_day_avg = df_1h['volume'].tail(24).mean()
        vol_spike_ratio = vol_recent_avg / vol_day_avg if vol_day_avg > 0 else 0
        
        is_high_vol = current_24h_vol > STD_MIN_VOL
        is_spike_vol = (current_24h_vol > SPIKE_MIN_VOL) and (vol_spike_ratio > VOL_SPIKE_RATIO)
        
        if not (is_high_vol or is_spike_vol):
            return {'status': 'Volume Filter', 'ticker': ticker}

        crazy_report = []
        crazy_cnt = 0
        if not df_1d.empty:
            df_1d['hl_ratio'] = df_1d['high'] / df_1d['low']
            crazy_days = df_1d[df_1d['hl_ratio'] >= CRAZY_DAY_THRESHOLD]
            crazy_cnt = len(crazy_days)
            
            # --- MODIFIED: PRIORITIZE DAILY DETAILS ---
            for date in crazy_days.index.sort_values(ascending=False)[:3]:
                date_str = date.strftime('%Y-%m-%d')
                
                # 1. Get Daily Details (Analysis Text) - PRIMARY
                daily_details = analyze_crazy_daily_context(ticker, date, df_1d, current_price)
                
                # 2. Get Hourly Details (Precision Stats) - SECONDARY
                hourly_details = analyze_crazy_event(ticker, date_str, df_1h)
                
                if daily_details:
                    # Enrich daily report with hourly precision volume if available
                    if hourly_details and hourly_details['vol_surge'] > 0:
                         # We keep is_detailed=False to FORCE the text block to render
                         daily_details['vol_surge'] = hourly_details['vol_surge'] 
                    crazy_report.append(daily_details)
                elif hourly_details:
                    # Fallback only if daily failed (unlikely)
                    crazy_report.append(hourly_details)

        df_1h, mean_p, mode_p, streak = calculate_metrics_chunk(df_1h.copy())
        df_1h, crosses, vol_trend = process_macro_data(df_1h)
        current_atr_1h = df_1h['ATR'].iloc[-1]
        avg_bb_width = df_1h['BB_Width_Pct'].tail(24).mean()
        current_adx = df_1h['ADX'].iloc[-1]
        ls_ratio = 1.0 

        atr_recent = df_1h['ATR'].tail(4).mean()
        atr_day = df_1h['ATR'].tail(24).mean()
        recent_vol_bonus = min(atr_recent / atr_day if atr_day > 0 else 1.0, 1.5)

        p_t1, p_t2, p_t3 = run_ensemble_models(df_1h)
        valid_preds = [p for p in [p_t1, p_t2, p_t3] if not np.isnan(p)]
        ai_center = sum(valid_preds) / len(valid_preds) if valid_preds else current_price

        daily_vol = current_atr_1h * 4.9
        safe_range = daily_vol * np.sqrt(GRID_TARGET_DAYS) * GRID_WIDTH_FACTOR
        grid_center = (current_price + ai_center) / 2
        l_grid = max(grid_center - safe_range, current_price * 0.5)
        u_grid = grid_center + safe_range
        
        micro_vol = calculate_micro_atr(df_1m, df_5m)
        step = micro_vol if micro_vol > 0 else current_price * 0.005
        opt_grids = int((u_grid - l_grid) / step)
        opt_grids = max(5, min(opt_grids, 149))

        score = avg_bb_width * crosses * recent_vol_bonus
        if current_adx > 50: score *= 0.5
        ls_score = 1.0 - min(abs(ls_ratio - 1.0), 0.5)
        score *= (0.5 + ls_score)
        if vol_spike_ratio > 1.5: score *= 1.2
        
        score *= funding_penalty
        pdrs_data = {}

        return {
            'status': 'OK',
            'Ticker': ticker.replace('/USDT', '').replace(':USDT', '').replace('*', ''),
            'Original_Ticker': ticker, 
            'Price': current_price, 'Mean': mean_p, 'Mode': mode_p,
            'L_Grd': l_grid, 'U_Grd': u_grid, 'Opt_G': opt_grids,
            'Score': int(score), 'Strk': int(streak),
            'T1': p_t1, 'T2': p_t2, 'T3': p_t3,
            'Vol_T': round(vol_trend, 2), 'LS_R': round(ls_ratio, 2), 'ADX': int(current_adx),
            'BB_W': round(avg_bb_width, 1), 'Cross': crosses,
            'Vol_Spike': round(vol_spike_ratio, 1), 'Recent_Vol': round(recent_vol_bonus, 2),
            'Crazy_Cnt': crazy_cnt, 'Crazy_Details': crazy_report,
            'Funding_Str': funding_str,
            'PDRS': pdrs_data 
        }
    except Exception as e:
        return {'status': f'Calc Error: {str(e)}', 'ticker': ticker}

def fetch_and_analyze_wrapper(ticker):
    try:
        d_1d = fetch_candles_logic(ticker, '1d', 365)
        d_1h = fetch_candles_logic(ticker, '1h', int(FIB_LOOKBACK_DAYS * 24 * 1.5))
        d_5m = fetch_candles_logic(ticker, '5m', 288)
        d_1m = fetch_candles_logic(ticker, '1m', 1440)
        return {'type': 'data', 'data': d_1d + d_1h + d_5m + d_1m, 'ticker': ticker}
    except Exception as e:
        return {'type': 'error', 'msg': str(e)}

def analyze_only_wrapper(ticker):
    try:
        df_1d = load_data_from_db(ticker, '1d', 365)
        df_1h = load_data_from_db(ticker, '1h', 500)
        df_5m = load_data_from_db(ticker, '5m', 288)
        df_1m = load_data_from_db(ticker, '1m', 1440)
        return process_ticker_logic(ticker, df_1d, df_1h, df_5m, df_1m)
    except: return None

def run_cycle():
    logging.info("--- Starting Radar Scan V10 (Detailed Risk + Funding + PDRS) ---")
    tickers = get_initial_tickers()
    logging.info(f"Identified {len(tickers)} candidates.")
    
    if not tickers:
        print("❌ CRITICAL: No tickers found to scan. Check network or API.")
        return

    print(f"\n[PHASE 1] Mass Downloading Data ({len(tickers)} Tickers)...")
    all_new_data = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(tqdm(executor.map(fetch_and_analyze_wrapper, tickers), total=len(tickers), unit="tick", colour="green"))
        for res in results:
            if res and res['type'] == 'data':
                all_new_data.extend(res['data'])
            
    print(f"\n[PHASE 2] Batch Saving {len(all_new_data)} records to SQLite...")
    save_batch_to_db(all_new_data)
    
    print(f"\n[PHASE 3] AI Analysis & Scoring (Max CPU)...")
    final_results = []
    statuses = []
    with ThreadPoolExecutor(max_workers=72) as executor:
        results = list(tqdm(executor.map(analyze_only_wrapper, tickers), total=len(tickers), unit="calc", colour="cyan"))
        for res in results:
            if res:
                statuses.append(res['status'])
                if res['status'] == 'OK':
                    final_results.append(res)
    
    status_counts = Counter(statuses)
    print(f"\n[SUMMARY] Scan Complete. Status: {dict(status_counts)}")
    
    if not final_results:
        logging.warning("No tickers passed filtering.")
        return

    top_picks = sorted(final_results, key=lambda x: x['Score'], reverse=True)[:10]
    
    if PDRS_AVAILABLE:
        print(f"\n[PHASE 4] Enrichment: Calculating PDRS for Top {len(top_picks)} Picks (CoinGecko Safe Mode)...")
        for i, p in enumerate(top_picks):
            try:
                orig_ticker = p.get('Original_Ticker')
                clean_ticker = p['Ticker']
                
                if orig_ticker:
                    df_pdrs = load_data_from_db(orig_ticker, '1h', limit=100)
                    
                    if not df_pdrs.empty:
                        print(f"   -> Fetching PDRS for {clean_ticker}...")
                        pdrs_res = pdrs_calculator.calculate_pdrs(clean_ticker, df_pdrs)
                        p['PDRS'] = pdrs_res
                        
                        if pdrs_res.get('score') == 0:
                             print(f"      ⚠️ {pdrs_res.get('risk_level')}: {pdrs_res.get('interpretation')}")
                        
                        time.sleep(2.0)
            except Exception as e:
                logging.error(f"PDRS Enrichment Failed for {p.get('Ticker', 'Unknown')}: {e}")

    headers = ["Ticker", "L_Grd", "U_Grd", "Score", "CrazyCnt"]
    rows = [[d['Ticker'], smart_format(d['L_Grd']), smart_format(d['U_Grd']), d['Score'], d['Crazy_Cnt']] for d in top_picks]
    print("\n" + tabulate(rows, headers=headers, tablefmt="simple"))
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header_msg = f"Mars Radar V10 (Neutral + PDRS)\nScan Time: {timestamp}\n"
    header_msg += f"Candidates: {len(tickers)} -> Passed: {len(final_results)}"
    
    body_lines = []
    
    for i, p in enumerate(top_picks, 1):
        t3_val = smart_format(p['T3']) 
        
        pdrs = p.get('PDRS', {})
        pdrs_score = pdrs.get('score', 0)
        pdrs_risk = pdrs.get('risk_level', 'N/A')
        pdrs_interp = pdrs.get('interpretation', 'No data')
        pdrs_pred = pdrs.get('prediction', '')
        
        risk_icon = "🟢" if pdrs_score < 40 else "🟡" if pdrs_score < 60 else "🔴"
        pdrs_block = ""
        if pdrs_score > 0:
            pdrs_block = (f" 📡 <b>[PDRS Risk Profile]</b>\n"
                          f"   • Score: <b>{pdrs_score}/100</b> {risk_icon} ({pdrs_risk})\n"
                          f"   • {pdrs_interp}\n")
            if pdrs_pred:
                pdrs_block += f"   • 🔮 {pdrs_pred}\n"
        
        risk_block = ""
        if p['Crazy_Cnt'] > 0:
            risk_block = f"⚠️ <b>Crazy History ({p['Crazy_Cnt']} times)</b>\n"
            if p.get('Crazy_Details'):
                for ev in p['Crazy_Details']:
                    pump_sym = "📈" if ev['pump_pct'] > 0 else "📉"
                    
                    if ev['is_detailed']:
                        vol_str = f"{ev['vol_surge']:.1f}x"
                        fib_sym = "❌ Broken" if ev['fib_broken'] else "✅ Held Supp"
                        risk_block += (f"   • {ev['date']}: {pump_sym} {ev['pump_pct']:.0f}% Move\n"
                                       f"     R: {smart_format(ev['low'])} -> {smart_format(ev['high'])}\n"
                                       f"     V: {vol_str} | {fib_sym}\n")
                    else:
                        aftermath = ev.get('aftermath', 'N/A')
                        result = ev.get('result', 'N/A')
                        
                        analysis_lines = ev.get('analysis_lines', [])
                        conclusion = ev.get('conclusion', '')
                        
                        analysis_str = "\n".join([f"      {l}" for l in analysis_lines])
                        
                        risk_block += (f"   • {ev['date']}: {pump_sym} {ev['pump_pct']:.0f}% Move\n"
                                       f"     R: {smart_format(ev['low'])} -> {smart_format(ev['high'])}\n"
                                       f"     {aftermath}\n"
                                       f"     ➡️ Result: {result}\n"
                                       f"     Analysis:\n{analysis_str}\n"
                                       f"     {conclusion}\n"
                                       f"     ----------------------------\n")
            else:
                risk_block += "   (Details unavailable)\n"
        else:
            risk_block = "✅ Safe History (1Y)"

        coin_block = (f"{i}. <b>{p['Ticker']}</b> | Score: {p['Score']} | Strk: {p['Strk']}\n"
                f" • Price: {smart_format(p['Price'])} | Mean: {smart_format(p['Mean'])} | Mode: {smart_format(p['Mode'])}\n"
                f" • Grid: {smart_format(p['L_Grd'])} - {smart_format(p['U_Grd'])} ({p['Opt_G']} Grids)\n"
                f" • AI Preds: T1:{smart_format(p['T1'])} | T2:{smart_format(p['T2'])} | T3:{t3_val}\n"
                f" • Stats: VolT:{p['Vol_T']} | LS:{p['LS_R']} | ADX:{p['ADX']}\n"
                f" • {p['Funding_Str']}\n"
                f" • Width: {p['BB_W']}% | Crosses: {p['Cross']} | Rec.Vol: {p['Recent_Vol']}x\n"
                f"{pdrs_block}"
                f"{risk_block}\n")
        body_lines.append(coin_block)
        
    send_telegram_alert(header_msg, body_lines)

if __name__ == "__main__":
    init_db()
    while True:
        try:
            run_cycle()
        except KeyboardInterrupt: break
        except Exception as e: logging.error(e)
        logging.info(f"Sleeping for {CHECK_INTERVAL_SECONDS}s...")
        time.sleep(CHECK_INTERVAL_SECONDS)