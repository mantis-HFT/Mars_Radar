# Quick Start Guide

Get Mars Radar V10 up and running in 5 minutes!

## Prerequisites

- Python 3.8+ installed
- Telegram account
- Basic command line knowledge

## Step-by-Step Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/mars-radar-v10.git
cd mars-radar-v10
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

**Note**: This may take a few minutes as it installs TensorFlow and other ML libraries.

### 3. Get Your Telegram Credentials

#### Create a Bot
1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot`
3. Follow the prompts to create your bot
4. Copy the bot token (looks like `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)

#### Get Your Chat ID
1. Search for [@userinfobot](https://t.me/userinfobot) on Telegram
2. Send `/start`
3. Copy your chat ID (looks like `123456789`)

### 4. Configure the Bot

```bash
cp config.ini.template config.ini
```

Edit `config.ini` and update these lines:

```ini
[radar_settings]
telegram_bot_token = YOUR_BOT_TOKEN_HERE
telegram_chat_ids = YOUR_CHAT_ID_HERE
```

**Example**:
```ini
telegram_bot_token = 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
telegram_chat_ids = 123456789
```

### 5. Start Mars Radar

```bash
python Mars_Radar_AI_Neutral.py
```

**First Run**: The bot will:
- Create a SQLite database
- Download initial market data (this may take 5-10 minutes)
- Run AI analysis
- Send alerts to your Telegram

### 6. Verify It's Working

Check your Telegram - you should receive a message like:

```
🚀 Mars Radar V10 (Neutral + PDRS)
Scan Time: 2025-02-14 15:30:00
Candidates: 145 -> Passed: 28

1. BTC | Score: 687 | Strk: 12
   • Price: 52,345.00 | Mean: 51,200.00
   • Grid: 49,800.00 - 54,900.00 (35 Grids)
   ...
```

## Basic Configuration

### Adjust Scan Frequency

Default: Every hour (3600 seconds)

```ini
check_interval_seconds = 3600   # 1 hour
check_interval_seconds = 1800   # 30 minutes
check_interval_seconds = 7200   # 2 hours
```

### Change Number of Alerts

Default: Top 10 coins

```ini
top_n_coins = 10   # Top 10
top_n_coins = 20   # Top 20
top_n_coins = 5    # Top 5 only
```

### Adjust Grid Width

Default: 2.0 (balanced)

```ini
grid_width_factor = 1.5   # Narrow (higher profit, higher risk)
grid_width_factor = 2.0   # Balanced (recommended)
grid_width_factor = 3.0   # Wide (safer, lower profit per grid)
```

## Understanding Your First Alert

### Example Alert Breakdown

```
1. PEPE | Score: 482 | Strk: 7
```
- **PEPE**: Ticker symbol
- **Score: 482**: Health metric (>200 is good, >400 is excellent)
- **Strk: 7**: Consecutive hours of positive momentum

```
Grid: 0.00001100 - 0.00001400 (30 Grids)
```
- **0.00001100**: Lower grid boundary (support)
- **0.00001400**: Upper grid boundary (resistance)
- **30 Grids**: Recommended number of grid levels

```
🟢 Score: 35/100 (LOW) - STABLE
```
- **35/100**: PDRS risk score
- **🟢 LOW**: Safe to trade (Green = Safe, Yellow = Caution, Red = Danger)

## Common Issues & Fixes

### "No module named 'tensorflow'"

**Fix**:
```bash
pip install tensorflow
```

### "Database is locked"

**Fix**: Make sure only one instance of Mars Radar is running
```bash
pkill -f Mars_Radar_AI_Neutral.py
python Mars_Radar_AI_Neutral.py
```

### "No tickers found to scan"

**Fix**: Check internet connection and exchange status
- Binance status: https://www.binance.com/en/support/announcement
- Bybit status: https://www.bybit.com/en-US/help-center/bybitStatus

### Rate Limit Errors

**Fix**: The bot has built-in rate limiting, but if you see errors:
1. Increase sleep time in config
2. Reduce the number of tickers
3. Wait 5-10 minutes and try again

## Next Steps

### 1. Read the Full Documentation
- [User Manual](docs/Mars_Radar_User_Manual.pdf) - Detailed signal interpretation
- [Technical Paper](docs/Mars_Radar_Technical_Paper.pdf) - AI architecture

### 2. Set Up Grid Trading
1. Open Binance or Bybit Futures
2. Navigate to "Grid Trading" or "Trading Bots"
3. Select "Neutral Grid" mode
4. Copy the `L_Grd` and `U_Grd` values from the alert
5. Set your investment amount
6. Start the grid bot

### 3. Monitor Performance
- Keep an eye on PDRS scores
- Avoid trading during RED alerts (PDRS > 60)
- Check "Crazy History" warnings for risky assets

### 4. Customize Parameters
Edit `config.ini` to:
- Change minimum volume thresholds
- Adjust volatility filters
- Enable/disable specific features

## Running in Production

### Background Process (Linux/Mac)

```bash
nohup python Mars_Radar_AI_Neutral.py > mars.log 2>&1 &
```

### Windows Service

Use Task Scheduler to run on startup.

### Docker (Advanced)

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "Mars_Radar_AI_Neutral.py"]
```

## Getting Help

- **Issues**: [GitHub Issues](https://github.com/yourusername/mars-radar-v10/issues)
- **Telegram**: [Mars Radar Community](https://t.me/mars_radar)
- **Email**: See README for contact info

## Safety Reminders

⚠️ **Important**:
- Start with small amounts
- Never risk more than you can afford to lose
- PDRS RED = Don't trade
- Always use stop-losses
- Monitor your bots regularly

---

**Happy Trading! 🚀**

Questions? Check the [FAQ](docs/FAQ.md) or open an issue.
