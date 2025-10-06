# tests/agents/test_technical_agent.py
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np

from app.agents.technical_agent import TechnicalAgent

# ---------- Fixtures ----------

@pytest.fixture
def agent():
    return TechnicalAgent("AAPL")

@pytest.fixture
def sample_df():
    dates = pd.date_range(end=pd.Timestamp.today(), periods=100)
    data = {
        'Open': np.random.rand(100) * 100,
        'High': np.random.rand(100) * 100,
        'Low': np.random.rand(100) * 100,
        'Close': np.random.rand(100) * 100,
        'Volume': np.random.randint(1e5, 1e6, 100)
    }
    return pd.DataFrame(data, index=dates)

# ---------- Happy Path Tests ----------

@patch("app.agents.technical_agent.yf.Ticker")
def test_resolve_symbol_direct_success(mock_ticker, agent, sample_df):
    mock_ticker.return_value.history.return_value = sample_df
    agent.resolve_symbol()
    assert agent.ticker == "AAPL"

@patch("app.agents.technical_agent.yf.Ticker")
def test_fetch_data_success(mock_ticker, agent, sample_df):
    mock_ticker.return_value.history.return_value = sample_df
    agent.ticker = "AAPL"
    df = agent.fetch_data()
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "Close" in df.columns

def test_compute_indicators(agent, sample_df):
    df_with_indicators = agent.compute_indicators(sample_df.copy())
    expected_cols = [
        "SMA_50", "EMA_20", "MACD", "MACD_Signal", "RSI_14",
        "BBU_20_2.0", "BBL_20_2.0", "ATR_14", "OBV", "VMA_20"
    ]
    for col in expected_cols:
        assert col in df_with_indicators.columns

def test_generate_summary_text(agent, sample_df):
    df_with_indicators = agent.compute_indicators(sample_df.copy())
    summary = agent.generate_summary_text(df_with_indicators)
    assert summary.startswith("Technical indicators for")
    assert "SMA_50" in summary
    assert "OBV" in summary

@patch("app.agents.technical_agent.GeminiClient.get_model")
def test_get_gemini_recommendation_success(mock_get_model, agent):
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"recommendation": "Buy", "summary": "Strong uptrend."}'
    mock_model.generate_content.return_value = mock_response
    mock_get_model.return_value = mock_model
    agent.model = mock_model

    result = agent.get_gemini_recommendation("summary text")
    assert result["recommendation"] == "Buy"
    assert "summary" in result

@patch("app.agents.technical_agent.yf.Ticker")
@patch("app.agents.technical_agent.GeminiClient.get_model")
def test_run_success(mock_get_model, mock_ticker, agent, sample_df):
    # Mock yfinance
    mock_ticker.return_value.history.return_value = sample_df
    agent.ticker = "AAPL"

    # Mock Gemini
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = '{"recommendation": "Hold", "summary": "Neutral signals."}'
    mock_model.generate_content.return_value = mock_response
    mock_get_model.return_value = mock_model
    agent.model = mock_model

    result = agent.run()
    assert "data" in result
    assert isinstance(result["data"], pd.DataFrame)
    assert "gemini" in result
    assert result["gemini"]["recommendation"] == "Hold"

# ---------- Error / Edge Case Tests ----------

# Resolve symbol errors
@patch("app.agents.technical_agent.yf.Ticker")
def test_resolve_symbol_yf_exception(mock_ticker, agent):
    mock_ticker.side_effect = Exception("Yahoo Finance failed")
    agent.resolve_symbol()
    assert agent.ticker is None

@patch("app.agents.technical_agent.yf.Ticker")
def test_resolve_symbol_suffix_failure(mock_ticker, agent):
    mock_ticker.return_value.history.return_value.empty = True
    agent.resolve_symbol()
    assert agent.ticker is None

@patch("app.agents.technical_agent.DDGS")
@patch("app.agents.technical_agent.yf.Ticker")
def test_resolve_symbol_ddgs_failure(mock_ticker, mock_ddgs, agent):
    mock_ticker.return_value.history.return_value.empty = True
    ddgs_instance = mock_ddgs.return_value.__enter__.return_value
    ddgs_instance.text.side_effect = Exception("DDGS failed")
    agent.resolve_symbol()
    assert agent.ticker is None

# Fetch data errors
@patch("app.agents.technical_agent.yf.Ticker")
def test_fetch_data_exception(mock_ticker, agent):
    agent.ticker = "AAPL"
    mock_ticker.side_effect = Exception("yfinance error")
    df = agent.fetch_data()
    assert df is None

@patch("app.agents.technical_agent.yf.Ticker")
def test_fetch_data_empty(mock_ticker, agent):
    agent.ticker = "AAPL"
    mock_ticker.return_value.history.return_value.empty = True
    df = agent.fetch_data()
    assert df is None

# Compute indicators exception
def test_compute_indicators_error(agent, sample_df):
    df = sample_df.copy()
    df['Close'] = None  # Break Close column to trigger ta exception
    df_result = agent.compute_indicators(df)
    assert df_result is not None

# Gemini JSON / Exception errors
@patch("app.agents.technical_agent.GeminiClient.get_model")
def test_get_gemini_recommendation_json_error(mock_get_model, agent):
    mock_model = mock_get_model.return_value
    response_mock = MagicMock()
    response_mock.text = "invalid json"
    mock_model.generate_content.return_value = response_mock
    agent.model = mock_model

    result = agent.get_gemini_recommendation("summary text")
    assert result["recommendation"] == "No recommendation available."
    assert result["summary"] == "No summary available due to an error."

# Run fallback when fetch_data returns None
def test_run_fetch_data_none(agent):
    agent.fetch_data = lambda: None
    result = agent.run()
    assert result is None
