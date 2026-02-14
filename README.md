# Mars Radar V10 🚀

An AI-Driven Architecture for Neutral Grid Optimization in Cryptocurrency Trading

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![TensorFlow](https://img.shields.io/badge/TensorFlow-2.x-orange.svg)](https://www.tensorflow.org/)

## Overview

Mars Radar V10 is a proprietary algorithmic market scanner designed to solve the "Range Selection Problem" in high-frequency Grid Trading. Unlike traditional trend-following systems, V10 focuses on defining high-probability volatility containment zones using hybrid ensemble learning and statistical risk modeling.

### Key Features

- 🤖 **AI Ensemble Engine**: Combines SARIMAX, LightGBM, and LSTM models for robust predictions
- 📊 **PDRS Algorithm**: Pump Dump Risk Score to detect "Blow-off Top" structures
- ⚡ **High Performance**: Multi-threaded architecture processes 100+ tickers in <15 seconds
- 💾 **Local Data Warehouse**: SQLite with WAL mode for efficient concurrent operations
- 📱 **Telegram Integration**: Real-time alerts with detailed market analysis
- 🎯 **Neutral Grid Strategy**: Profit from volatility regardless of price direction

## System Architecture

### Data Pipeline
- Multi-threaded `ThreadPoolExecutor` for parallel processing
- CCXT integration for Binance and Bybit exchanges
- Local SQLite database for historical data storage
- Automatic API rate limit handling and failover

### AI Models

1. **SARIMAX** (Seasonal Auto-Regressive Integrated Moving Average)
   - Captures linear trends and seasonality
   - Configuration: Order (1,1,1)

2. **LightGBM** (Gradient Boosting Machine)
   - Captures non-linear dependencies
   - Features: Price lags, volatility metrics

3. **LSTM** (Long Short-Term Memory Network)
   - Temporal sequence learning
   - Architecture: 10-step lookback, 20 LSTM units

### PDRS Risk Engine

The Pump Dump Risk Score (PDRS) quantifies tail risks on a 0-100 scale using 5 KPIs:

- **Volatility Ratio**: Standard deviation of 1H returns
- **Acceleration**: Second derivative proxy for momentum
- **Parabolic Extension**: Distance from 24-period SMA
- **Momentum Persistence**: Green vs Red candle ratio
- **Beta Correlation**: Correlation with Bitcoin

Formula:
```
PDRS = 0.3(V_R) + 0.1(Accel) + 0.3(Ext) + 0.15(Persist) + 0.15(Beta)
```

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Dependencies

```bash
pip install numpy pandas ccxt requests pycoingecko
pip install tensorflow keras scikit-learn lightgbm
pip install statsmodels pandas-ta tabulate tqdm
```

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/mars-radar-v10.git
cd mars-radar-v10
```

2. Copy the configuration template:
```bash
cp config.ini.template config.ini
```

3. Edit `config.ini` and add your credentials:
   - Get Telegram bot token from [@BotFather](https://t.me/BotFather)
   - Get your chat ID from [@userinfobot](https://t.me/userinfobot)

4. Initialize the database:
```bash
python Mars_Radar_AI_Neutral.py
```

## Configuration

### Telegram Settings

```ini
[radar_settings]
telegram_bot_token = YOUR_BOT_TOKEN_HERE
telegram_chat_ids = YOUR_CHAT_ID_HERE
```

### Grid Strategy Parameters

```ini
grid_target_days = 3.0          # Expected runtime (days)
grid_width_factor = 2.0         # Safety coefficient (1.5-3.0)
min_profit_per_grid = 0.002     # Minimum 0.2% profit per grid
```

### Risk Filters

```ini
standard_min_volume = 15000000  # Minimum volume (USD)
volume_spike_ratio = 3.0        # Spike detection threshold
crazy_day_threshold = 3.0       # Volatility danger threshold
```

## Usage

### Basic Usage

Run the scanner once:
```bash
python Mars_Radar_AI_Neutral.py
```

### Continuous Monitoring

The bot will automatically run in a loop based on `check_interval_seconds` (default: 3600s/1 hour).

### Reading Signals

A typical Mars Radar alert contains:

1. **Header**: Momentum score and trend streak
   ```
   PEPE | Score: 482 | Strk: 7
   ```

2. **Grid Range**: Critical for setting up your bot
   ```
   Grid: 0.00001100 - 0.00001400 (30 Grids)
   ```

3. **AI Predictions**: Ensemble model outputs
   ```
   AI Preds: T1: 1320 | T2: 1290 | T3: 1350
   ```

4. **PDRS Risk Profile**: Safety indicator
   ```
   🔴 Score: 82/100 (HIGH) - EXTREME PARABOLIC
   ```

5. **Historical Analysis**: Past behavior patterns
   ```
   ⚠️ Crazy History (1 times) - Crashed to Fib 78.6%
   ```

## Risk Management

### Trading Guidelines

- ✅ **GREEN PDRS (0-40)**: Safe for entry
- ⚠️ **YELLOW PDRS (41-60)**: Use tight stop-losses
- 🛑 **RED PDRS (61+)**: DO NOT open neutral grid

### Best Practices

1. Never trade during RED PDRS alerts
2. Check funding rates before entry
3. Set stop-loss slightly outside suggested grid range
4. Avoid low-volume coins (< $15M daily volume)
5. Monitor "Crazy History" warnings

## File Structure

```
mars-radar-v10/
├── Mars_Radar_AI_Neutral.py    # Main scanner script
├── pdrs_calculator.py          # PDRS risk engine
├── config.ini.template         # Configuration template
├── README.md                   # This file
├── requirements.txt            # Python dependencies
├── docs/                       # Documentation
│   ├── Technical_Paper.pdf     # Academic architecture paper
│   ├── User_Manual.pdf         # Detailed user guide
│   └── video_scripts/          # Video tutorial scripts
└── .gitignore                  # Git ignore rules
```

## Performance

- **Throughput**: 100+ tickers with 4 timeframes in <15 seconds
- **Accuracy**: Ensemble voting reduces model bias
- **Efficiency**: WAL-mode SQLite for concurrent operations
- **Reliability**: Automatic failover between exchanges

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Disclaimer

⚠️ **Important**: This software is for educational and research purposes only. Cryptocurrency trading carries significant risk. Never invest more than you can afford to lose. The authors are not responsible for any financial losses incurred through the use of this software.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [CCXT](https://github.com/ccxt/ccxt) for exchange connectivity
- Powered by [TensorFlow](https://www.tensorflow.org/) and [LightGBM](https://lightgbm.readthedocs.io/)
- Market data from [CoinGecko API](https://www.coingecko.com/en/api)

## Contact

For questions, suggestions, or support:
- Create an issue on GitHub
- Join our Telegram channel: [Mars Radar Community](https://t.me/mars_radar)

---

**Made with ❤️ for the crypto trading community**
