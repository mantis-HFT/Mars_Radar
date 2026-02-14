import numpy as np
import pandas as pd
import requests
import time
import logging
from pycoingecko import CoinGeckoAPI
from datetime import datetime, timedelta

# Initialize CoinGecko API
cg = CoinGeckoAPI()

# Cache for Bitcoin history to avoid repeating calls
BTC_HISTORY_CACHE = None
BTC_CACHE_TIME = 0

def get_coingecko_id(symbol):
    """
    Attempts to find the CoinGecko ID from a ticker symbol.
    Enhanced mapping to include common radar targets and fix search ambiguities.
    """
    # 1. Basic cleaning
    # Remove futures suffixes
    symbol = symbol.lower().replace('-usd', '').replace('/usdt', '').split(':')[0]
    
    # 2. Handle '1000' or 'k' prefix (common in futures, e.g. 1000PEPE -> PEPE)
    # Check if starts with 1000 and the remaining part is a valid looking ticker (len > 2)
    if symbol.startswith('1000') and len(symbol) > 4:
        symbol = symbol[4:]
    elif symbol.startswith('k') and len(symbol) > 3: # e.g. kBONK
        symbol = symbol[1:]

    # Manual overrides for accuracy and speed
    # USER: Add missing coins here if the error says "ID ERROR"
    mapping = {
        'btc': 'bitcoin', 'eth': 'ethereum', 'sol': 'solana',
        'bnb': 'binancecoin', 'xrp': 'ripple', 'doge': 'dogecoin',
        'ada': 'cardano', 'link': 'chainlink', 'dot': 'polkadot',
        'matic': 'matic-network', 'ltc': 'litecoin', 'uni': 'uniswap',
        'river': 'river', 'siren': 'siren', 'pnut': 'peanut-the-squirrel',
        'virtual': 'virtual-protocol', 'pengu': 'pudgy-penguins',
        'goat': 'goatseus-maximus', 'act': 'act-i-the-ai-prophecy',
        
        # --- Common Missing Ones ---
        'brev': 'brevis-network', 
        'skr': 'skr', 
        'enso': 'enso-finance',
        'neiro': 'neiro-on-eth',
        'moodeng': 'moodeng-on-eth',
        'cow': 'cow-protocol',
        'safe': 'safe-coin',
        'troy': 'troy',
        'turbo': 'turbo',
        'eigen': 'eigenlayer'
    }
    
    if symbol in mapping:
        return mapping[symbol]
    
    try:
        # Search API fallback
        results = cg.search(query=symbol)
        for coin in results.get('coins', []):
            # Strict matching to avoid getting 'bitcoin-cash' when searching for 'bitcoin'
            if coin['symbol'].lower() == symbol:
                return coin['id']
    except Exception:
        pass
    return None

def get_bitcoin_history():
    """Fetches last 30 days of BTC history for correlation analysis."""
    global BTC_HISTORY_CACHE, BTC_CACHE_TIME
    if BTC_HISTORY_CACHE is not None and (time.time() - BTC_CACHE_TIME < 3600):
        return BTC_HISTORY_CACHE
    
    try:
        data = cg.get_coin_market_chart_by_id(id='bitcoin', vs_currency='usd', days=30)
        prices = [p[1] for p in data['prices']]
        BTC_HISTORY_CACHE = pd.Series(prices)
        BTC_CACHE_TIME = time.time()
        return BTC_HISTORY_CACHE
    except Exception as e:
        logging.error(f"Failed to fetch BTC history: {e}")
        return None

def get_ticker_data(cg_id):
    """Fetches high-level market data for a specific coin."""
    try:
        data = cg.get_coin_market_chart_by_id(id=cg_id, vs_currency='usd', days=30)
        prices = [p[1] for p in data['prices']]
        volumes = [v[1] for v in data['total_volumes']]
        return pd.Series(prices), pd.Series(volumes)
    except Exception as e:
        logging.error(f"Failed to fetch data for {cg_id}: {e}")
        return None, None

def calculate_pdrs(ticker_symbol, df_1h=None):
    """
    Enhanced PDRS Calculator (V3) - ENGLISH VERSION
    Aligned with Mars Radar Main Brain
    """
    try:
        cg_id = get_coingecko_id(ticker_symbol)
        
        # --- SMART ERROR FEEDBACK ---
        if not cg_id:
            return {
                'score': 0, 
                'risk_level': 'ID ERROR',
                'details': 'N/A',
                'interpretation': f"⚠️ CoinGecko ID not found for '{ticker_symbol}'. Check 'mapping' in pdrs_calculator.py.",
                'prediction': ""
            }

        prices_30d, volumes_30d = get_ticker_data(cg_id)
        if prices_30d is None or df_1h is None or len(df_1h) < 24:
            return {'score': 0, 'risk_level': 'NO DATA', 'interpretation': 'Insufficient history for PDRS.', 'prediction': ''}

        # --- KPI 1: VOLATILITY ---
        returns_1h = df_1h['close'].pct_change().fillna(0)
        volatility = returns_1h.std() * 100 
        n_vr = np.nan_to_num(min(100, volatility * 5))

        # --- KPI 2: ACCELERATION ---
        last_move = returns_1h.iloc[-1] * 100
        avg_move = returns_1h.abs().mean() * 100
        acceleration = abs(last_move) / (avg_move + 1e-9)
        n_accel = np.nan_to_num(min(100, acceleration * 10))

        # --- KPI 3: PARABOLIC EXTENSION ---
        sma_24 = df_1h['close'].rolling(window=24).mean().iloc[-1]
        extension_ratio = (df_1h['close'].iloc[-1] / sma_24) if sma_24 > 0 else 1
        n_ext = np.nan_to_num(min(100, max(0, (extension_ratio - 1.2) * 60)))

        # --- KPI 4: MOMENTUM PERSISTENCE ---
        recent_12 = returns_1h.tail(12)
        green_count = (recent_12 > 0).sum()
        n_persist = np.nan_to_num((green_count / 12) * 100)

        # --- KPI 5: BTC Correlation ---
        btc_prices = get_bitcoin_history()
        n_laf = 50 
        if btc_prices is not None:
            min_len = min(len(prices_30d), len(btc_prices))
            corr = prices_30d.tail(min_len).corr(btc_prices.tail(min_len))
            n_laf = np.nan_to_num((1 - abs(corr)) * 100)

        # --- AGGREGATE SCORE ---
        pdrs = (n_vr * 0.3) + (n_accel * 0.1) + (n_ext * 0.3) + (n_persist * 0.15) + (n_laf * 0.15)
        pdrs = min(100, round(pdrs, 1))

        # --- INTERPRETATION & PREDICTION (Professional English) ---
        curr_price = df_1h['close'].iloc[-1]
        max_30d = prices_30d.max()
        min_30d = prices_30d.min()

        # Translate Interpretations
        if pdrs > 75:
            interpretation = "EXTREME PARABOLIC: Price overheated. Critical 'Blow-off Top' risk."
        elif pdrs > 50:
            interpretation = "STRONG MOMENTUM: Trend is healthy but accelerating into Resistance."
        elif n_vr > 70:
            interpretation = "HIGH VOLATILITY: Heavy Whale Accumulation or Distribution detected."
        else:
            interpretation = "STABLE: Market is in Accumulation or Sideways zone."

        # Translate Predictions
        if curr_price < (max_30d * 0.5):
            target = curr_price * 1.3
            prediction = f"Potential Bottom formation. Short-term target: ${target:.4f}. Hard Support: ${min_30d:.4f}."
        else:
            resistance = max_30d * 1.1
            prediction = f"Trend Extension. Next Resistance: ${resistance:.4f}. Take profit zone if PDRS > 80."
        
        # Translate Risk Level
        if pdrs > 60:
            r_level = 'HIGH'
        elif pdrs > 40:
            r_level = 'MEDIUM'
        else:
            r_level = 'LOW'

        return {
            'score': pdrs,
            'risk_level': r_level,
            'details': f"V:{int(n_vr)} E:{int(n_ext)} P:{int(n_persist)} L:{int(n_laf)}",
            'interpretation': interpretation,
            'prediction': prediction
        }
    except Exception as e:
        logging.error(f"PDRS Calculation failed for {ticker_symbol}: {e}")
        return {'score': 0, 'risk_level': 'SYSTEM ERROR'}