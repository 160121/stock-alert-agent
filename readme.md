# 📈 Stock Agent  

An AI-powered **stock analysis assistant** that integrates **technical analysis, fundamental analysis, and sentiment analysis** into a unified **Decision Agent**.  
Built with **Python, yFinance, Gemini API, Streamlit, and Telegram Bot**, this project helps users make informed investment decisions with a clean UI and bot integration.  

---

## ✨ Features  

- 📊 **Technical Analysis**  
  - Fetches stock data using `yfinance`  
  - Generates indicators (RSI, MACD, Bollinger Bands, SMA, EMA, etc.)  
  - Provides AI-powered insights  

- 💰 **Fundamental Analysis**  
  - Company financials (P/E, EPS, Revenue, Market Cap, Balance Sheet, etc.)  
  - News & filings summarization using **Gemini API**  

- 📰 **Sentiment Analysis**  
  - Fetches latest news using DuckDuckGo Search (`ddgs`)  
  - AI-powered classification into **positive / negative / neutral sentiment**  
  - Sentiment scoring  

- 🧠 **Decision Agent**  
  - Combines technical, fundamental, and sentiment signals  
  - Produces an **actionable recommendation**: Buy / Sell / Hold  
  - Explains reasoning  

- 💻 **Streamlit Web App**  
  - Interactive dashboard  
  - Enter ticker symbols and get instant insights  
  - Deployed on: [https://stock-alert-agent-by-navya.streamlit.app](https://stock-alert-agent-by-navya.streamlit.app)  

- 🤖 **Telegram Bot Integration**  
  - Query stock tickers directly from Telegram https://t.me/Navyasree_proj_bot
  - Get insights on the go  
  - opt-in for daily updates
---

---

## 🚀 Getting Started  

### 1️⃣ Clone the repo  
```bash
git clone https://githyd.epam.com/marepalli_navyasree/stock-agent.git
cd stock-agent
```
### 2️⃣ Create a virtual environment 
```bash
python -m venv venv
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate      # Windows
```
### 3️⃣ Install dependencies 
```bash
pip install -r requirements.txt

```
### 4️⃣ Setup Environment Variables
```bash
GEMINI_API_KEY=your_api_key_here
TELEGRAM_BOT_TOKEN=your_bot_token_here
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

```
### 5️⃣ Run Streamlit App
```bash
streamlit run ui/streamlit_app.py

```
### 6️⃣ Run Telegram Bot (optional)
```bash
python app/services/telegram_service.py

```
--------

crafted with ❤️ by Navyasree


