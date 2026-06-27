import streamlit as st

# Set page configurations
st.set_page_config(
    page_title="Bitcoin Trading Coach",
    page_icon="🪙",
    layout="centered"
)

# Application Title
st.title("🪙 Bitcoin Trading Coach")

# Welcome Message
st.markdown("""
### Welcome to your Bitcoin Trading Coach!
This application acts as a 3-agent orchestration system to scan the Bitcoin market, generate coaching charts, and execute sandbox/production trades securely.

**Core Agents in action:**
1. **Analyst Agent** - Scans market charts for key support/resistance levels.
2. **Coach Agent** - Renders visual candlestick charts with Entry, Stop-Loss, and Take-Profit boundaries.
3. **Execution Agent** - Manages API orders securely after your manual confirmation.
""")

st.divider()

# Market Scan Action Button
if st.button("🔍 Scan Market Now", type="primary"):
    st.info("Market scan requested! Analyst Agent starting check on BTC 4-hour/Daily charts...")
    # Placeholder for Agent logic integration
    st.warning("Note: Trading and scanning agents are not yet linked to the UI. Please check back as development continues!")
