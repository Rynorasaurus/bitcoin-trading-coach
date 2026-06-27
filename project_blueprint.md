# Project Blueprint: Bitcoin Trading Coach
**Objective:** Build a 3-agent system for the Kaggle 5-Day AI Agents Capstone Project.
**Track:** Concierge Agents
**Environment:** Google Cloud (Cloud Run)

## 1. Architectural Directives
* **Git Workflow (Strict):** NEVER push directly to `main`. Every new feature must be developed on a separate feature branch. The agent must explicitly ask for user permission before merging into `main`.
* **Security (Ironclad):** API keys must never be hardcoded. Use the established `.env` file (which is in `.gitignore`). Maintain strict separation between Sandbox (Kraken Testnet) and Production environments.
* **Error Handling:** Keep logs lightweight. Print clear, plain-English error messages directly to the terminal or UI if a process fails. 
* **State (Memory):** The application is stateless. It generates real-time analysis on demand with no persistent database for past trades.
* **User Interface:** A Streamlit web portal with a manual, on-demand "Scan Market Now" button.

## 2. Core Agent Chain
1. **Analyst Agent (The Scanner):** Uses the TradingView MCP to scan 4-hour/Daily BTC charts for support/resistance levels.
2. **Coach Agent (The Visual Teacher):** Uses Python (`matplotlib`) to generate a candlestick chart with Entry (Green), Stop-Loss (Red), and Take-Profit (Blue) lines.
3. **Execution Agent (The Gatekeeper):** Uses the Kraken MCP. Requires a strict, manual "CONFIRM" input from the user before passing the payload to the API.
