# Security Policy

## Protecting Your Credentials

Mars Radar V10 requires API access to exchanges and Telegram. Follow these guidelines to keep your credentials secure:

### ⚠️ CRITICAL SECURITY RULES

1. **NEVER commit `config.ini` to Git**
   - The `.gitignore` file is configured to exclude it
   - Always use `config.ini.template` as a reference
   - Keep your actual `config.ini` local only

2. **Telegram Bot Token**
   - Get it from [@BotFather](https://t.me/BotFather)
   - Treat it like a password - never share it
   - If exposed, revoke it immediately via BotFather

3. **Exchange API Keys** (if you extend the code)
   - Use read-only API keys when possible
   - Enable IP whitelist restrictions
   - Never share or commit API secrets

### Best Practices

#### Configuration Management

```bash
# DO: Use the template
cp config.ini.template config.ini
nano config.ini  # Edit with your credentials

# DON'T: Add config.ini to Git
git add config.ini  # ❌ NEVER DO THIS
```

#### Environment Variables (Alternative Method)

For production deployments, consider using environment variables:

```python
import os

TELEGRAM_BOT_TOKEN = os.getenv('MARS_TELEGRAM_TOKEN', '')
TELEGRAM_CHAT_IDS = os.getenv('MARS_CHAT_IDS', '').split(',')
```

Then set them in your shell:
```bash
export MARS_TELEGRAM_TOKEN="your_token_here"
export MARS_CHAT_IDS="chat_id_1,chat_id_2"
```

### Database Security

- The SQLite database (`market_data_radar_n.db`) contains only market data
- No credentials are stored in the database
- Use file permissions to protect it: `chmod 600 market_data_radar_n.db`

### Network Security

- Mars Radar connects to:
  - Binance API (`api.binance.com`)
  - Bybit API (`api.bybit.com`)
  - CoinGecko API (`api.coingecko.com`)
  - Telegram API (`api.telegram.org`)
  
- All connections use HTTPS/TLS encryption
- Consider using a VPN for additional privacy
- Monitor firewall logs for unusual activity

### Reporting Security Issues

If you discover a security vulnerability:

1. **DO NOT** open a public GitHub issue
2. Email the maintainers privately (see README for contact)
3. Include:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

We will respond within 48 hours and work to address valid issues promptly.

### Secure Deployment Checklist

- [ ] `config.ini` is not tracked by Git
- [ ] Telegram bot token is kept private
- [ ] File permissions are restrictive (`chmod 600 config.ini`)
- [ ] Running on a secure, updated system
- [ ] Firewall is configured properly
- [ ] Logs do not contain sensitive data
- [ ] Regular backups of configuration (stored securely)

### Updates and Patches

- Watch this repository for security updates
- Update dependencies regularly: `pip install -r requirements.txt --upgrade`
- Check for CCXT library updates (exchange API changes)

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 10.x    | :white_check_mark: |
| < 10.0  | :x:                |

---

**Remember**: Security is a shared responsibility. Stay vigilant and follow best practices.
