# Contributing to Mars Radar V10

First off, thank you for considering contributing to Mars Radar! It's people like you that make this project better for everyone.

## Code of Conduct

This project and everyone participating in it is governed by our commitment to:
- Be respectful and inclusive
- Welcome constructive feedback
- Focus on what's best for the community
- Show empathy towards others

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When creating a bug report, include:

- **Clear title**: Summarize the problem
- **Description**: Detailed explanation of the issue
- **Steps to reproduce**: How to trigger the bug
- **Expected behavior**: What should happen
- **Actual behavior**: What actually happens
- **Environment**: OS, Python version, dependency versions
- **Logs**: Relevant error messages or logs

Example:
```markdown
**Title**: LSTM model fails with small datasets

**Description**: When running with less than 50 candles, the LSTM model throws a shape error.

**Steps to Reproduce**:
1. Set lookback to 100 days for a newly listed coin
2. Run the scanner
3. Observe error

**Error Log**:
```
ValueError: Input 0 of layer "sequential" is incompatible with the layer...
```

**Environment**: Ubuntu 22.04, Python 3.10.8, TensorFlow 2.11.0
```

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, include:

- **Use case**: Why is this enhancement needed?
- **Proposed solution**: How should it work?
- **Alternatives**: Other approaches you've considered
- **Additional context**: Screenshots, examples, etc.

### Pull Requests

1. **Fork the repository**
   ```bash
   git clone https://github.com/yourusername/mars-radar-v10.git
   cd mars-radar-v10
   ```

2. **Create a branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```

3. **Make your changes**
   - Follow the coding style guide below
   - Add tests if applicable
   - Update documentation

4. **Commit your changes**
   ```bash
   git commit -m 'Add amazing feature'
   ```

5. **Push to your fork**
   ```bash
   git push origin feature/amazing-feature
   ```

6. **Open a Pull Request**

## Coding Style Guide

### Python Code Style

Follow [PEP 8](https://pep8.org/) with these specifics:

- **Indentation**: 4 spaces (no tabs)
- **Line length**: Max 100 characters
- **Naming**:
  - Functions: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_CASE`
  - Variables: `snake_case`

### Code Structure

```python
# Good: Clear function with docstring
def calculate_grid_range(price, volatility, factor=2.0):
    """
    Calculate grid trading range based on price and volatility.
    
    Args:
        price (float): Current asset price
        volatility (float): Historical volatility metric
        factor (float): Width multiplier (default: 2.0)
    
    Returns:
        tuple: (lower_bound, upper_bound)
    """
    spread = price * volatility * factor
    return (price - spread, price + spread)

# Bad: No docstring, unclear variable names
def calc(p, v, f=2.0):
    s = p * v * f
    return (p - s, p + s)
```

### Comments

- Use comments to explain **why**, not **what**
- Keep comments up-to-date with code changes
- Avoid obvious comments

```python
# Good: Explains reasoning
# Use exponential moving average to reduce noise in volatile markets
ema_price = df['close'].ewm(span=20).mean()

# Bad: States the obvious
# Calculate exponential moving average
ema_price = df['close'].ewm(span=20).mean()
```

### Error Handling

Always handle exceptions gracefully:

```python
# Good: Specific exception handling
try:
    data = exchange.fetch_ohlcv(symbol, '1h')
except ccxt.NetworkError as e:
    logging.error(f"Network error fetching {symbol}: {e}")
    return None
except ccxt.ExchangeError as e:
    logging.error(f"Exchange error for {symbol}: {e}")
    return None

# Bad: Bare except
try:
    data = exchange.fetch_ohlcv(symbol, '1h')
except:
    pass
```

## Development Setup

### Local Development Environment

1. **Clone and install**
   ```bash
   git clone https://github.com/yourusername/mars-radar-v10.git
   cd mars-radar-v10
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure**
   ```bash
   cp config.ini.template config.ini
   # Edit config.ini with your test credentials
   ```

3. **Run tests** (when test suite is available)
   ```bash
   pytest tests/
   ```

### Testing Guidelines

- Write tests for new features
- Ensure existing tests pass
- Include edge cases
- Test with different market conditions

```python
def test_grid_calculation():
    """Test grid range calculation with normal volatility."""
    lower, upper = calculate_grid_range(100, 0.1, 2.0)
    assert lower == 80.0
    assert upper == 120.0

def test_grid_calculation_high_volatility():
    """Test grid range calculation with extreme volatility."""
    lower, upper = calculate_grid_range(100, 0.5, 2.0)
    assert lower == 0.0  # Should not go negative
    assert upper == 200.0
```

## Documentation

### Code Documentation

- Add docstrings to all functions, classes, and modules
- Use Google-style docstrings
- Include examples in docstrings when helpful

### README Updates

If your change affects user-facing functionality:
- Update README.md
- Add examples
- Update configuration sections

## Areas for Contribution

We especially welcome contributions in:

### 1. **Model Improvements**
- Alternative AI models (Prophet, GRU, Transformer)
- Hyperparameter optimization
- Feature engineering

### 2. **Exchange Support**
- Additional exchanges via CCXT
- Spot trading support
- Options/derivatives

### 3. **Risk Management**
- Advanced PDRS variations
- Portfolio-level risk metrics
- Dynamic position sizing

### 4. **Performance Optimization**
- Database query optimization
- Caching strategies
- Parallel processing improvements

### 5. **User Interface**
- Web dashboard
- Mobile app integration
- Enhanced Telegram bot features

### 6. **Testing & Quality**
- Unit tests
- Integration tests
- Backtesting validation

### 7. **Documentation**
- Tutorial videos
- Example configurations
- Trading strategy guides

## Commit Message Guidelines

Use clear, descriptive commit messages:

```
feat: Add support for Kraken exchange
fix: Resolve LSTM shape error with small datasets
docs: Update installation instructions for Windows
refactor: Simplify grid calculation logic
test: Add unit tests for PDRS calculator
```

Prefixes:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code restructuring
- `test`: Adding or updating tests
- `perf`: Performance improvements
- `chore`: Maintenance tasks

## Questions?

Feel free to:
- Open an issue for questions
- Join our Telegram community
- Email the maintainers (see README)

Thank you for contributing to Mars Radar! 🚀
