import pytest
from unittest.mock import patch, MagicMock
from app.agents.fundamental_agent import FundamentalAgent

# ---------- Fixtures ----------

@pytest.fixture
def agent():
    return FundamentalAgent("AAPL")

# ---------- Happy Path Tests ----------

def test_generate_summary_text(agent):
    sample_data = {"market_cap": 2500000000, "pe_ratio": 28.5}
    summary = agent.generate_summary_text(sample_data)
    assert "market_cap: 2500000000" in summary
    assert "pe_ratio: 28.5" in summary
    assert summary.startswith("Fundamental metrics for")

@patch("app.agents.fundamental_agent.yf.Ticker")
def test_fetch_data_success(mock_ticker, agent):
    mock_ticker.return_value.info = {
        "marketCap": 1000000,
        "trailingPE": 20,
        "forwardPE": 18,
        "pegRatio": 1.5,
        "dividendYield": 0.02,
        "beta": 1.1,
        "totalRevenue": 500000,
        "grossProfits": 200000,
        "operatingMargins": 0.25,
        "netIncomeToCommon": 100000,
        "debtToEquity": 0.4
    }
    agent.ticker = "AAPL"
    data = agent.fetch_data()
    assert data["market_cap"] == 1000000
    assert "pe_ratio" in data

@patch("app.agents.fundamental_agent.yf.Ticker")
def test_resolve_symbol_direct_success(mock_ticker, agent):
    mock_ticker.return_value.history.return_value.empty = False
    agent.resolve_symbol()
    assert agent.ticker == "AAPL"

@patch("app.agents.fundamental_agent.DDGS")
@patch("app.agents.fundamental_agent.yf.Ticker")
def test_resolve_symbol_duckduckgo_success(mock_ticker, mock_ddgs, agent):
    # Simulate all direct ticker checks fail
    mock_ticker.return_value.history.return_value.empty = True

    # Mock DuckDuckGo to return a valid Yahoo symbol
    ddgs_instance = MagicMock()
    ddgs_instance.__enter__.return_value.text.return_value = [{"url": "https://finance.yahoo.com/quote/XYZ"}]
    mock_ddgs.return_value = ddgs_instance

    # Mock yfinance.Ticker for resolved symbol XYZ to succeed
    def ticker_side_effect(ticker):
        mock_t = MagicMock()
        if ticker == "XYZ":
            mock_t.history.return_value.empty = False
        else:
            mock_t.history.return_value.empty = True
        return mock_t

    mock_ticker.side_effect = ticker_side_effect

    agent.resolve_symbol()
    assert agent.ticker == "XYZ"


@patch("app.agents.fundamental_agent.GeminiClient.get_model")
def test_get_gemini_recommendation_success(mock_get_model, agent):
    mock_model = mock_get_model.return_value
    response_mock = MagicMock()
    response_mock.text = '{"recommendation": "Buy", "summary": "Strong financials."}'
    mock_model.generate_content.return_value = response_mock
    agent.model = mock_model

    result = agent.get_gemini_recommendation("Sample text")
    assert result["recommendation"] == "Buy"
    assert "summary" in result

@patch("app.agents.fundamental_agent.GeminiClient.get_model")
@patch("app.agents.fundamental_agent.yf.Ticker")
def test_run_success(mock_ticker, mock_get_model, agent):
    mock_ticker.return_value.info = {"marketCap": 1000000, "trailingPE": 20}
    mock_model = MagicMock()
    response_mock = MagicMock()
    response_mock.text = '{"recommendation": "Buy", "summary": "Solid fundamentals."}'
    mock_model.generate_content.return_value = response_mock
    mock_get_model.return_value = mock_model
    agent.model = mock_model

    agent.ticker = "AAPL"
    result = agent.run()
    assert "data" in result
    assert "gemini" in result
    assert result["gemini"]["recommendation"] == "Buy"

# ---------- Error / Edge Case Tests ----------

@patch("app.agents.fundamental_agent.yf.Ticker")
def test_resolve_symbol_yf_exception(mock_ticker, agent):
    mock_ticker.side_effect = Exception("Yahoo Finance failed")
    agent.resolve_symbol()
    assert agent.ticker is None

@patch("app.agents.fundamental_agent.yf.Ticker")
def test_resolve_symbol_suffix_failure(mock_ticker, agent):
    mock_ticker.return_value.history.return_value.empty = True
    agent.resolve_symbol()
    assert agent.ticker is None

@patch("app.agents.fundamental_agent.DDGS")
@patch("app.agents.fundamental_agent.yf.Ticker")
def test_resolve_symbol_ddgs_failure(mock_ticker, mock_ddgs, agent):
    mock_ticker.return_value.history.return_value.empty = True
    ddgs_instance = mock_ddgs.return_value.__enter__.return_value
    ddgs_instance.text.side_effect = Exception("DDGS failed")
    agent.resolve_symbol()
    assert agent.ticker is None

@patch("app.agents.fundamental_agent.yf.Ticker")
def test_fetch_data_exception(mock_ticker, agent):
    agent.ticker = "AAPL"
    mock_ticker.side_effect = Exception("yfinance error")
    data = agent.fetch_data()
    assert data is None

@patch("app.agents.fundamental_agent.GeminiClient.get_model")
def test_get_gemini_recommendation_json_error(mock_get_model, agent):
    mock_model = mock_get_model.return_value
    response_mock = MagicMock()
    response_mock.text = "invalid json"
    mock_model.generate_content.return_value = response_mock
    agent.model = mock_model

    result = agent.get_gemini_recommendation("sample text")
    assert result["recommendation"] == "No recommendation available."
    assert result["summary"] == "No summary available due to an error."
