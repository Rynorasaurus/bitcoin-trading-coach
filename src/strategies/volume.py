import pandas as pd

def analyze_strategy(bars):
    """
    Analyzes trading volume spikes and buying/selling climax.
    Args:
        bars (list): List of OHLCV bars.
    Returns:
        dict: Analysis result with signal and details.
    """
    if not bars or len(bars) < 20: # Require at least 20 bars to compute average volume
        return {
            "strategy": "Volume",
            "signal": "NEUTRAL",
            "details": "Insufficient data to calculate volume averages (requires at least 20 bars)."
        }
        
    df = pd.DataFrame(bars)
    
    # Calculate 20-period average volume
    avg_volume = df['volume'].rolling(window=20).mean()
    current_volume = df['volume'].iloc[-1]
    last_avg_volume = avg_volume.iloc[-1]
    
    # We define a "climax" or "spike" if volume is greater than 2x the 20-period average
    if current_volume > 2.0 * last_avg_volume:
        # Determine if it is a buying or selling climax
        close_price = df['close'].iloc[-1]
        open_price = df['open'].iloc[-1]
        
        if close_price > open_price:
            signal = "BUY"
            details = f"Buying Climax / Bullish Volume Spike detected! Vol: {current_volume:.2f} is {current_volume / last_avg_volume:.1f}x the 20-bar avg ({last_avg_volume:.2f})."
        else:
            signal = "SELL"
            details = f"Selling Climax / Bearish Volume Spike detected! Vol: {current_volume:.2f} is {current_volume / last_avg_volume:.1f}x the 20-bar avg ({last_avg_volume:.2f})."
    else:
        signal = "NEUTRAL"
        details = f"Volume is normal at {current_volume:.2f} ({current_volume / last_avg_volume:.1f}x the 20-bar avg of {last_avg_volume:.2f})."
        
    return {
        "strategy": "Volume",
        "signal": signal,
        "details": details
    }
