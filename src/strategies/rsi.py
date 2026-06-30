import pandas as pd

def analyze_strategy(bars):
    """
    Analyzes RSI (Relative Strength Index) indicator conditions.
    Args:
        bars (list): List of OHLCV bars.
    Returns:
        dict: Analysis result with signal and details.
    """
    if not bars or len(bars) < 15:
        return {
            "strategy": "RSI",
            "signal": "NEUTRAL",
            "details": "Insufficient data to calculate RSI (requires at least 15 bars)."
        }
        
    df = pd.DataFrame(bars)
    
    # Calculate RSI
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    # Standard Wilder's RSI using rolling/exponential averages
    avg_gain = gain.ewm(com=13, adjust=False).mean()
    avg_loss = loss.ewm(com=13, adjust=False).mean()
    
    rs = avg_gain / avg_loss.replace(0, 1e-9) # Avoid division by zero
    rsi = 100 - (100 / (1 + rs))
    
    current_rsi = rsi.iloc[-1]
    
    # Signal threshold logic
    if current_rsi < 30:
        signal = "BUY"
        details = f"Oversold conditions detected. RSI is {current_rsi:.2f} (< 30)."
    elif current_rsi > 70:
        signal = "SELL"
        details = f"Overbought conditions detected. RSI is {current_rsi:.2f} (> 70)."
    else:
        signal = "NEUTRAL"
        details = f"RSI is neutral at {current_rsi:.2f} (within 30-70 range)."
        
    return {
        "strategy": "RSI",
        "signal": signal,
        "details": details
    }
