import pandas as pd

def analyze_strategy(bars):
    """
    Analyzes MACD (Moving Average Convergence Divergence) crossovers.
    Args:
        bars (list): List of OHLCV bars.
    Returns:
        dict: Analysis result with signal and details.
    """
    if not bars or len(bars) < 35: # Require enough bars to stabilize EMAs
        return {
            "strategy": "MACD",
            "signal": "NEUTRAL",
            "details": "Insufficient data to calculate MACD (requires at least 35 bars)."
        }
        
    df = pd.DataFrame(bars)
    
    # Calculate MACD
    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    
    hist = macd_line - signal_line
    
    # Get last two values to check for crossover
    prev_hist = hist.iloc[-2]
    curr_hist = hist.iloc[-1]
    curr_macd = macd_line.iloc[-1]
    curr_sig = signal_line.iloc[-1]
    
    # Crossover check
    if prev_hist < 0 and curr_hist >= 0:
        signal = "BUY"
        details = f"Bullish MACD Crossover: MACD line crossed above Signal line. Histogram: {curr_hist:.4f} (Prev: {prev_hist:.4f})."
    elif prev_hist > 0 and curr_hist <= 0:
        signal = "SELL"
        details = f"Bearish MACD Crossover: MACD line crossed below Signal line. Histogram: {curr_hist:.4f} (Prev: {prev_hist:.4f})."
    else:
        signal = "NEUTRAL"
        trend = "Bullish" if curr_hist > 0 else "Bearish"
        details = f"No crossover detected. Trend is currently {trend}. MACD: {curr_macd:.4f}, Signal: {curr_sig:.4f}."
        
    return {
        "strategy": "MACD",
        "signal": signal,
        "details": details
    }
