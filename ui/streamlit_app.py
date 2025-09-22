# ui/streamlit_app.py
import sys
import os

# Ensure project root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import streamlit as st
import asyncio
from app.agents.decision_agent import DecisionAgent

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
    }
    .analysis-section {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    .sentiment-positive {
        color: #28a745;
        font-weight: bold;
    }
    .sentiment-negative {
        color: #dc3545;
        font-weight: bold;
    }
    .sentiment-neutral {
        color: #6c757d;
        font-weight: bold;
    }
    .decision-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin: 2rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Helper to run async functions in sync context
def run_async(func, *args, **kwargs):
    return asyncio.run(func(*args, **kwargs))

def display_sentiment_badge(sentiment):
    """Display sentiment with appropriate styling"""
    if sentiment.lower() in ['positive', 'bullish']:
        return f'<span class="sentiment-positive">🟢 {sentiment.upper()}</span>'
    elif sentiment.lower() in ['negative', 'bearish']:
        return f'<span class="sentiment-negative">🔴 {sentiment.upper()}</span>'
    else:
        return f'<span class="sentiment-neutral">🟡 {sentiment.upper()}</span>'

def main():
    st.set_page_config(
        page_title="Stock Analysis Dashboard", 
        layout="wide",
        page_icon="📈",
        initial_sidebar_state="collapsed"
    )
    
    st.markdown("""
    <div class="main-header">
        <h1>📈 Professional Stock Analysis Dashboard</h1>
        <p>Advanced AI-powered technical, fundamental, and sentiment analysis for informed investment decisions</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        ticker = st.text_input(
            "Enter Stock Ticker Symbol", 
            placeholder="e.g., AAPL, TSLA, MSFT, GOOGL",
            help="Enter a valid stock ticker symbol to get comprehensive analysis"
        ).strip().upper()
    
    if ticker:
        st.markdown(f"""
        <div style="text-align: center; padding: 1rem; background: #e9ecef; border-radius: 10px; margin: 1rem 0;">
            <h2>📊 Analysis Results for: <span style="color: #667eea;">{ticker}</span></h2>
        </div>
        """, unsafe_allow_html=True)
        
        with st.spinner("🔄 Running comprehensive analysis... Please wait"):
            agent = DecisionAgent(ticker)
            try:
                results = run_async(agent.run)

                col1, col2, col3 = st.columns(3)

                # Technical Analysis
                tech = agent.get_technical_result()
                if tech:
                    with col1:
                        st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
                        st.subheader("🔧 Technical Analysis")
                        
                        gemini_data = tech.get("gemini", {})
                        if gemini_data:
                            for key, value in gemini_data.items():
                                st.markdown(f"""
                                <div class="metric-card">
                                    <strong>{key.replace('_', ' ').title()}:</strong><br>
                                    {value}
                                </div>
                                """, unsafe_allow_html=True)
                        
                        if tech.get("data") is not None:
                            with st.expander("📈 Technical Data Details"):
                                st.dataframe(tech.get("data"), width='stretch')
                        
                        st.markdown('</div>', unsafe_allow_html=True)

                # Sentiment Analysis
                sent = agent.get_sentiment_result()
                if sent:
                    with col2:
                        st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
                        st.subheader("📰 Sentiment Analysis")
                        
                        overall_sentiment = sent.get(ticker, {}).get("overall_sentiment", "N/A")
                        st.markdown(f"""
                        <div class="metric-card" style="text-align: center;">
                            <h3>Overall Market Sentiment</h3>
                            {display_sentiment_badge(overall_sentiment)}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        news_list = sent.get(ticker, {}).get("news", [])
                        if news_list:
                            st.markdown("### 📰 Recent News Analysis")
                            for i, news in enumerate(news_list[:5]):  # Show top 5 news
                                sentiment_badge = display_sentiment_badge(news.get('sentiment', 'Neutral'))
                                st.markdown(f"""
                                <div style="background: #f8f9fa; padding: 1rem; border-radius: 8px; margin: 0.5rem 0;">
                                    <strong><a href="{news.get('url', '#')}" target="_blank">{news.get('title', 'No Title')}</a></strong><br>
                                    <small>Sentiment: {sentiment_badge}</small>
                                </div>
                                """, unsafe_allow_html=True)
                        
                        st.markdown('</div>', unsafe_allow_html=True)

                # Fundamental Analysis
                fund = agent.get_fundamental_result()
                if fund:
                    with col3:
                        st.markdown('<div class="analysis-section">', unsafe_allow_html=True)
                        st.subheader("📊 Fundamental Analysis")
                        
                        gemini_data = fund.get("gemini", {})
                        if gemini_data:
                            for key, value in gemini_data.items():
                                st.markdown(f"""
                                <div class="metric-card">
                                    <strong>{key.replace('_', ' ').title()}:</strong><br>
                                    {value}
                                </div>
                                """, unsafe_allow_html=True)
                        
                        data = fund.get("data", {})
                        if data:
                            # Separate available and unavailable metrics
                            available_metrics = {k: v for k, v in data.items() if v is not None}
                            unavailable_metrics = [k for k, v in data.items() if v is None]

                            if available_metrics:
                                st.markdown("### ✅ Available Indicators")
                                for k, v in available_metrics.items():
                                    st.markdown(f"""
                                    <div style="background: #e3f2fd; padding: 0.8rem; border-radius: 6px; margin: 0.3rem 0;">
                                        <strong>{k.replace('_', ' ').title()}:</strong> {v}
                                    </div>
                                    """, unsafe_allow_html=True)

                            if unavailable_metrics:
                                with st.expander("❌ Unavailable Indicators"):
                                    st.markdown("These indicators are either not applicable for this stock or not provided by the data source.")
                                    for k in unavailable_metrics:
                                        readable_key = k.replace('_', ' ').title()
                                        st.markdown(f"""
                                        <div style="background: #f8d7da; padding: 0.8rem; border-radius: 6px; margin: 0.3rem 0;">
                                            <strong>{readable_key}:</strong> 
                                            <span style="color: #dc3545;">Not Available</span>
                                            <span title="This data may be unavailable because it's not provided by the data source or doesn't apply to this company."> ℹ️</span>
                                        </div>
                                        """, unsafe_allow_html=True)
                        
                        st.markdown('</div>', unsafe_allow_html=True)

                final_decision = agent.get_final_decision()
                if final_decision:
                    st.markdown("""
                    <div class="decision-card">
                        <h2>💡 AI Investment Recommendation</h2>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    dec_col1, dec_col2 = st.columns(2)
                    
                    with dec_col1:
                        decision = final_decision.get('final_decision', 'N/A')
                        decision_color = "#28a745" if "buy" in decision.lower() else "#dc3545" if "sell" in decision.lower() else "#ffc107"
                        st.markdown(f"""
                        <div style="background: {decision_color}; color: white; padding: 1.5rem; border-radius: 10px; text-align: center;">
                            <h3>🎯 Decision</h3>
                            <h2>{decision}</h2>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with dec_col2:
                        reasoning = final_decision.get('reasoning', 'N/A')
                        st.markdown(f"""
                        <div style="background: #f8f9fa; padding: 1.5rem; border-radius: 10px;">
                            <h3>🧠 AI Reasoning</h3>
                            <p>{reasoning}</p>
                        </div>
                        """, unsafe_allow_html=True)

                st.markdown("---")
                footer_col1, footer_col2, footer_col3 = st.columns(3)
                
                with footer_col1:
                    if st.button("🔄 Analyze Another Stock", type="primary"):
                        st.experimental_rerun()
                
                with footer_col2:
                    st.markdown("""
                    <div style="text-align: center; padding: 1rem;">
                        <small>⚠️ This analysis is for informational purposes only.<br>
                        Not financial advice. Please consult a financial advisor.</small>
                    </div>
                    """, unsafe_allow_html=True)
                
                with footer_col3:
                    if st.button("🌐 Visit Streamlit"):
                        js = "window.open('https://streamlit.io', '_blank').focus();"
                        st.components.v1.html(f"<script>{js}</script>", height=0, width=0)
                
            except Exception as e:
                st.error(f"❌ Error running analysis: {e}")
                st.info("💡 Please check your internet connection and try again with a valid stock ticker.")

if __name__ == "__main__":
    main()
