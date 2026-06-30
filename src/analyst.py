import sys
import json
import subprocess
import requests
import pandas as pd
import concurrent.futures
from src.strategies import rsi, macd, volume, stair_step

TRADINGVIEW_CLI_PATH = "/home/rynor/tradingview-mcp/src/cli/index.js"

def check_tradingview_status():
    """Checks if TradingView Desktop is running and responsive."""
    try:
        result = subprocess.run(
            ["node", TRADINGVIEW_CLI_PATH, "status"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            status_data = json.loads(result.stdout)
            return status_data.get("connected", False)
    except Exception:
        pass
    return False

def get_ohlcv_from_tradingview():
    """Fetches OHLCV data from TradingView Desktop."""
    try:
        result = subprocess.run(
            ["node", TRADINGVIEW_CLI_PATH, "ohlcv"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            bars = data.get("bars", [])
            formatted_bars = []
            for bar in bars:
                formatted_bars.append({
                    "time": bar.get("time"),
                    "open": float(bar.get("open")),
                    "high": float(bar.get("high")),
                    "low": float(bar.get("low")),
                    "close": float(bar.get("close")),
                    "volume": float(bar.get("volume", 0))
                })
            return formatted_bars
    except Exception as e:
        print(f"Error reading TradingView chart: {e}", file=sys.stderr)
    return None

def get_ohlcv_from_kraken():
    """Fallback: Fetches OHLCV data from Kraken's public REST API."""
    try:
        url = "https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=240"  # 4h
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f"Error: Kraken API returned status code {response.status_code}", file=sys.stderr)
            return None
        
        data = response.json()
        if "error" in data and data["error"]:
            print(f"Kraken API error: {', '.join(data['error'])}", file=sys.stderr)
            return None
            
        result = data.get("result", {})
        pair_key = [k for k in result.keys() if k != "last"][0]
        bars = result[pair_key]
        
        formatted_bars = []
        for bar in bars[-100:]:  # Take the last 100 bars
            formatted_bars.append({
                "time": int(bar[0]),
                "open": float(bar[1]),
                "high": float(bar[2]),
                "low": float(bar[3]),
                "close": float(bar[4]),
                "volume": float(bar[6])
            })
        return formatted_bars
    except Exception as e:
        print(f"Error fetching fallback Kraken data: {e}", file=sys.stderr)
    return None

def calculate_levels(bars):
    """Calculates Support/Resistance levels and current price from OHLCV bars."""
    if not bars:
        return None
        
    df = pd.DataFrame(bars)
    current_price = df["close"].iloc[-1]
    
    recent_df = df.tail(20)
    resistance_level = recent_df["high"].max()
    support_level = recent_df["low"].min()
    
    if support_level == current_price:
        support_level *= 0.99
    if resistance_level == current_price:
        resistance_level *= 1.01
        
    return {
        "current_price": current_price,
        "support_level": support_level,
        "resistance_level": resistance_level,
        "bars": bars
    }

def run_strategies_concurrently(bars):
    """Triggers all 4 specialized technical strategy agents simultaneously."""
    strategies = [
        ("RSI", rsi.analyze_strategy),
        ("MACD", macd.analyze_strategy),
        ("Volume", volume.analyze_strategy),
        ("Stair-Step", stair_step.analyze_strategy)
    ]
    
    results = {}
    print("Analyst Agent: Orchestrating strategy executions concurrently...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        future_to_strategy = {
            executor.submit(func, bars): name 
            for name, func in strategies
        }
        
        for future in concurrent.futures.as_completed(future_to_strategy):
            name = future_to_strategy[future]
            try:
                results[name] = future.result()
            except Exception as e:
                print(f"Error executing strategy {name}: {e}", file=sys.stderr)
                results[name] = {
                    "strategy": name,
                    "signal": "ERROR",
                    "details": f"Failed to execute strategy: {str(e)}"
                }
    return results

def run_analysis():
    """Runs the full Analyst Agent pipeline, including concurrent strategies."""
    print("Analyst Agent: Initializing market scan...")
    
    is_tv_running = check_tradingview_status()
    bars = None
    source = "Public Kraken API (Fallback)"
    
    if is_tv_running:
        print("Analyst Agent: Connected to TradingView Desktop. Fetching chart data...")
        bars = get_ohlcv_from_tradingview()
        if bars:
            source = "TradingView Desktop"
    
    if not bars:
        if is_tv_running:
            print("Analyst Agent: Could not read TradingView chart. Falling back...", file=sys.stderr)
        else:
            print("Analyst Agent: TradingView Desktop not running. Using fallback...")
        bars = get_ohlcv_from_kraken()
        
    if not bars:
        print("Error: Failed to retrieve market data from all sources.", file=sys.stderr)
        return None
        
    analysis = calculate_levels(bars)
    if analysis:
        analysis["source"] = source
        print(f"Analyst Agent: Scan complete. Source: {source}")
        print(f"Analyst Agent: Current Price = ${analysis['current_price']:.2f}")
        print(f"Analyst Agent: Support Level = ${analysis['support_level']:.2f}")
        print(f"Analyst Agent: Resistance Level = ${analysis['resistance_level']:.2f}")
        
        # Run specialized strategies concurrently
        strategy_signals = run_strategies_concurrently(bars)
        analysis["strategy_signals"] = strategy_signals
        
        # Print summary of results
        print("Analyst Agent: Concurreny strategy analysis results:")
        for name, res in strategy_signals.items():
            print(f"  - [{name}]: {res['signal']} | {res['details']}")
            
    return analysis

if __name__ == "__main__":
    result = run_analysis()
    if not result:
        sys.exit(1)

