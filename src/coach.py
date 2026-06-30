import sys
import os
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
import google.generativeai as genai

def generate_trading_setup(current_price, support_level, resistance_level):
    """Calculates entry, stop-loss, and take-profit targets."""
    # Determine bias based on price location within the trading range
    midpoint = (support_level + resistance_level) / 2.0
    
    if current_price < midpoint:
        # Buy/Long bias: Price is closer to support
        bias = "BUY / LONG"
        entry = current_price
        # Stop loss is set 1.5% below support to avoid fakeouts
        stop_loss = support_level * 0.985
        # Take profit is set slightly below resistance
        take_profit = resistance_level * 0.99
    else:
        # Sell/Short bias: Price is closer to resistance
        bias = "SELL / SHORT"
        entry = current_price
        # Stop loss is set 1.5% above resistance
        stop_loss = resistance_level * 1.015
        # Take profit is set slightly above support
        take_profit = support_level * 1.01
        
    return {
        "bias": bias,
        "entry": entry,
        "stop_loss": stop_loss,
        "take_profit": take_profit
    }

def draw_candlestick_chart(bars, setup, output_path="src/coach_chart.png"):
    """Generates a beautiful candlestick chart with trade setup overlays."""
    try:
        # Limit to the last 40 bars for clean visual display
        df = pd.DataFrame(bars).tail(40).copy()
        
        # Convert unix timestamps to string labels
        # Check if timestamps are in seconds or milliseconds
        sample_time = df["time"].iloc[0]
        if sample_time > 1e11:  # milliseconds
            df["datetime"] = df["time"].apply(lambda x: datetime.fromtimestamp(x / 1000.0).strftime('%m-%d %H:%M'))
        else:
            df["datetime"] = df["time"].apply(lambda x: datetime.fromtimestamp(x).strftime('%m-%d %H:%M'))
            
        df = df.reset_index(drop=True)
        
        # Setup the plot
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(11, 6), dpi=150)
        
        # Plot candlesticks
        for idx, row in df.iterrows():
            color = "#00c49f" if row["close"] >= row["open"] else "#ff3f66"
            # Draw wick (high to low)
            ax.vlines(idx, row["low"], row["high"], color=color, linewidth=1.5)
            # Draw body (open to close)
            lower_body = min(row["open"], row["close"])
            height = abs(row["open"] - row["close"])
            if height == 0:
                height = 0.5  # Ensure flat bars are visible
            rect = plt.Rectangle((idx - 0.3, lower_body), 0.6, height, facecolor=color, edgecolor=color)
            ax.add_patch(rect)
            
        # Draw Trade Setup lines
        entry = setup["entry"]
        stop_loss = setup["stop_loss"]
        take_profit = setup["take_profit"]
        
        # Entry (Green)
        ax.axhline(entry, color="#00ff00", linestyle="--", linewidth=1.5, label=f"Entry: ${entry:.2f}")
        # Stop Loss (Red)
        ax.axhline(stop_loss, color="#ff0000", linestyle="-.", linewidth=1.5, label=f"Stop-Loss: ${stop_loss:.2f}")
        # Take Profit (Blue)
        ax.axhline(take_profit, color="#0088ff", linestyle="-.", linewidth=1.5, label=f"Take-Profit: ${take_profit:.2f}")
        
        # Formatting
        ax.set_title(f"BTC/USD 4H Chart - Trade Setup Plan ({setup['bias']})", fontsize=14, color="#ffffff", pad=15)
        ax.set_xticks(range(0, len(df), max(1, len(df)//8)))
        ax.set_xticklabels([df["datetime"].iloc[i] for i in range(0, len(df), max(1, len(df)//8))], rotation=30, ha="right", fontsize=9)
        
        ax.set_ylabel("Price (USD)", fontsize=11)
        ax.grid(True, color="#333333", linestyle=":", alpha=0.6)
        
        # Legend (transparent background)
        legend = ax.legend(loc="upper left", framealpha=0.2, facecolor="#000000")
        for text in legend.get_texts():
            text.set_color("white")
            
        plt.tight_layout()
        
        # Save to disk
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, facecolor="#0e1117", edgecolor="none")
        plt.close()
        
        print(f"Coach Agent: Candlestick chart successfully generated and saved to: {output_path}")
        return True
    except Exception as e:
        print(f"Error drawing candlestick chart: {e}", file=sys.stderr)
        return False

def run_coach(analysis_data):
    """Runs the full Coach Agent pipeline."""
    print("Coach Agent: Analyzing levels and calculating setup...")
    
    current_price = analysis_data["current_price"]
    support_level = analysis_data["support_level"]
    resistance_level = analysis_data["resistance_level"]
    bars = analysis_data.get("bars", [])
    
    setup = generate_trading_setup(current_price, support_level, resistance_level)
    print(f"Coach Agent: Setup calculated -> Recommendation: {setup['bias']}")
    print(f"Coach Agent: Target Entry = ${setup['entry']:.2f}")
    print(f"Coach Agent: Target Stop-Loss = ${setup['stop_loss']:.2f}")
    print(f"Coach Agent: Target Take-Profit = ${setup['take_profit']:.2f}")
    
    if bars:
        draw_candlestick_chart(bars, setup)
        
    return setup

def answer_coach_question(question, analysis_data, setup_data):
    """Answers user questions about the trading setup using the Gemini API or a smart fallback."""
    # Check for Gemini API key in environment
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    
    if api_key and not api_key.startswith("your_"):
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.5-flash")
            
            # Format strategy signals safely
            signals = analysis_data.get("strategy_signals", {})
            rsi_sig = signals.get("RSI", {}).get("signal", "NEUTRAL")
            rsi_det = signals.get("RSI", {}).get("details", "")
            macd_sig = signals.get("MACD", {}).get("signal", "NEUTRAL")
            macd_det = signals.get("MACD", {}).get("details", "")
            vol_sig = signals.get("Volume", {}).get("signal", "NEUTRAL")
            vol_det = signals.get("Volume", {}).get("details", "")
            stair_sig = signals.get("Stair-Step", {}).get("signal", "NEUTRAL")
            stair_det = signals.get("Stair-Step", {}).get("details", "")

            prompt = f"""
You are the Coach Agent in a 3-agent Bitcoin trading system.
Your job is to explain the current market scan and trade setup plan to the user in a friendly, educational, and plain-English tone.

Current Market Data:
- Price: ${analysis_data['current_price']:.2f}
- Support Level: ${analysis_data['support_level']:.2f}
- Resistance Level: ${analysis_data['resistance_level']:.2f}
- Data Source: {analysis_data.get('source', 'Unknown')}

Individual Strategy Agent Signals:
- RSI Agent: {rsi_sig} ({rsi_det})
- MACD Agent: {macd_sig} ({macd_det})
- Volume Agent: {vol_sig} ({vol_det})
- Stair-Step Agent: {stair_sig} ({stair_det})

Proposed Trade Setup Plan:
- Recommendation Bias: {setup_data['bias']}
- Target Entry: ${setup_data['entry']:.2f}
- Stop-Loss: ${setup_data['stop_loss']:.2f}
- Take-Profit: ${setup_data['take_profit']:.2f}

User Question: "{question}"

Provide a concise, detailed, and plain-English explanation. Answer the question directly using the market data and strategy signals context. Keep it under 4 sentences if possible.
"""
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Coach Agent: Gemini API call failed ({e}). Using smart fallback...", file=sys.stderr)
            
    # Smart pre-configured rule-based fallback
    q_low = question.lower()
    if "macd" in q_low:
        return (
            "The MACD Agent currently shows a NEUTRAL signal because we are in the skeletal phase. "
            "Once fully implemented, the MACD Agent will scan for momentum crossovers (when the MACD line "
            "crosses the Signal line) on the 4H/Daily chart to confirm trend strength."
        )
    elif "rsi" in q_low:
        return (
            "The RSI Agent is currently NEUTRAL. Once configured, it will detect overbought (>70) or "
            "oversold (<30) conditions. Currently, price is inside the support/resistance range, representing "
            "a neutral stance."
        )
    elif "volume" in q_low:
        return (
            "The Volume Agent reports NEUTRAL. In the future, this agent will analyze trading volume spikes "
            "to check for buying or selling exhaustion near support or resistance levels."
        )
    elif "stair" in q_low or "step" in q_low:
        return (
            "The Stair-Step Agent is looking for market continuation patterns. Since it's in skeletal mode, "
            "it reports NEUTRAL. When active, it will confirm if the market is printing higher highs/higher lows "
            "for longs, or lower highs/lower lows for shorts."
        )
    elif "stop" in q_low or "loss" in q_low:
        return (
            f"The Stop-Loss is set at ${setup_data['stop_loss']:.2f}. "
            f"This is positioned 1.5% outside of the trading range boundary to protect your capital. "
            "If price breaks past this level, it invalidates our trade setup."
        )
    elif "take" in q_low or "profit" in q_low:
        return (
            f"The Take-Profit target is set at ${setup_data['take_profit']:.2f}. "
            "This target is positioned just inside the opposite range boundary, maximizing expected returns "
            "while ensuring a high probability of execution before the trend reverses."
        )
    else:
        return (
            f"As your Coach, I calculated a **{setup_data['bias']}** plan based on the trading range "
            f"between ${analysis_data['support_level']:.2f} (Support) and ${analysis_data['resistance_level']:.2f} (Resistance). "
            f"The current price is ${analysis_data['current_price']:.2f}. "
            "Feel free to ask specific questions about 'RSI', 'MACD', 'Volume', 'Stair-Step', 'Stop-Loss', or 'Take-Profit'!"
        )

if __name__ == "__main__":
    # Test stub with sample data
    sample_analysis = {
        "current_price": 60700.0,
        "support_level": 58000.0,
        "resistance_level": 63000.0,
        "bars": [
            {"time": 1720000000 + i*14400, "open": 59000 + i*100, "high": 59500 + i*100, "low": 58800 + i*100, "close": 59200 + i*100, "volume": 1000}
            for i in range(40)
        ]
    }
    run_coach(sample_analysis)
