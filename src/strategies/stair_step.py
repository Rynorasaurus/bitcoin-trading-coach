import pandas as pd

def analyze_strategy(bars):
    """
    Analyzes price action for stair-step continuation patterns.
    Args:
        bars (list): List of OHLCV bars.
    Returns:
        dict: Analysis result with signal and details.
    """
    if not bars or len(bars) < 3: # Require at least 3 bars
        return {
            "strategy": "Stair-Step",
            "signal": "NEUTRAL",
            "details": "Insufficient data to calculate price action patterns (requires at least 3 bars)."
        }
        
    df = pd.DataFrame(bars)
    
    # Get last 3 bars
    b2 = df.iloc[-3] # 2 bars ago
    b1 = df.iloc[-2] # 1 bar ago
    b0 = df.iloc[-1] # Current bar
    
    # Bullish Stair-Step: Consecutive Higher Highs AND Higher Lows
    is_bullish = (b0["high"] > b1["high"] > b2["high"]) and (b0["low"] > b1["low"] > b2["low"])
    
    # Bearish Stair-Step: Consecutive Lower Highs AND Lower Lows
    is_bearish = (b0["high"] < b1["high"] < b2["high"]) and (b0["low"] < b1["low"] < b2["low"])
    
    if is_bullish:
        signal = "BUY"
        details = (
            f"Bullish Continuation (Higher Highs & Higher Lows) detected over the last 3 bars. "
            f"Highs: ${b2['high']:.2f} -> ${b1['high']:.2f} -> ${b0['high']:.2f}. "
            f"Lows: ${b2['low']:.2f} -> ${b1['low']:.2f} -> ${b0['low']:.2f}."
        )
    elif is_bearish:
        signal = "SELL"
        details = (
            f"Bearish Continuation (Lower Highs & Lower Lows) detected over the last 3 bars. "
            f"Highs: ${b2['high']:.2f} -> ${b1['high']:.2f} -> ${b0['high']:.2f}. "
            f"Lows: ${b2['low']:.2f} -> ${b1['low']:.2f} -> ${b0['low']:.2f}."
        )
    else:
        signal = "NEUTRAL"
        details = "No stair-step continuation pattern detected (price action is consolidating or choppy)."
        
    return {
        "strategy": "Stair-Step",
        "signal": signal,
        "details": details
    }
