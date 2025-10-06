# tests/agents/test_sentiment_agent.py
import pytest
from unittest.mock import patch, MagicMock

from app.agents.sentiment_agent import SentimentAgent

# ---------- Fixtures ----------

@pytest.fixture
def agent():
    return SentimentAgent(["AAPL", "TSLA"])

@pytest.fixture
def sample_articles():
    return [
        {"title": "Apple rises", "source": "News1", "date": "2025-10-05", "url": "http://example.com/aapl1"},
        {"title": "Tesla dips", "source": "News2", "date": "2025-10-05", "url": "http://example.com/tsla1"},
    ]

# ---------- Happy Path Tests ----------

@patch("app.agents.sentiment_agent.DDGS")
def test_fetch_news_success(mock_ddgs, agent, sample_articles):
    ddgs_instance = mock_ddgs.return_value.__enter__.return_value
    ddgs_instance.news.return_value = sample_articles

    result = agent.fetch_news("AAPL")
    assert isinstance(result, list)
    assert len(result) == len(sample_articles)
    assert result[0]["title"] == "Apple rises"

@patch("app.agents.sentiment_agent.GeminiClient.get_model")
def test_analyze_sentiment_success(mock_get_model, agent, sample_articles):
    mock_model = MagicMock()
    response_mock = MagicMock()
    response_mock.text = '{"overall_sentiment": "Positive", "news": [{"title": "Apple rises", "source": "News1", "date": "2025-10-05", "url": "http://example.com/aapl1", "sentiment": "Positive"}]}'
    mock_model.generate_content.return_value = response_mock
    mock_get_model.return_value = mock_model
    agent.model = mock_model

    result = agent.analyze_sentiment(sample_articles)
    assert result["overall_sentiment"] == "Positive"
    assert len(result["news"]) == 1
    assert result["news"][0]["sentiment"] == "Positive"

def test_analyze_sentiment_empty_articles(agent):
    result = agent.analyze_sentiment([])
    assert result["overall_sentiment"] == "Neutral"
    assert result["news"] == []

@patch("app.agents.sentiment_agent.DDGS")
@patch("app.agents.sentiment_agent.GeminiClient.get_model")
def test_run_success(mock_get_model, mock_ddgs, agent, sample_articles):
    # Mock news fetch
    ddgs_instance = mock_ddgs.return_value.__enter__.return_value
    ddgs_instance.news.return_value = sample_articles

    # Mock Gemini
    mock_model = MagicMock()
    response_mock = MagicMock()
    response_mock.text = '{"overall_sentiment": "Neutral", "news": [{"title": "Apple rises", "source": "News1", "date": "2025-10-05", "url": "http://example.com/aapl1", "sentiment": "Neutral"}]}'
    mock_model.generate_content.return_value = response_mock
    mock_get_model.return_value = mock_model
    agent.model = mock_model

    results = agent.run()
    assert "AAPL" in results
    assert "TSLA" in results
    for symbol_result in results.values():
        assert "overall_sentiment" in symbol_result
        assert "news" in symbol_result

# ---------- Error / Edge Case Tests ----------

@patch("app.agents.sentiment_agent.DDGS")
def test_fetch_news_exception(mock_ddgs, agent):
    ddgs_instance = mock_ddgs.return_value.__enter__.return_value
    ddgs_instance.news.side_effect = Exception("DuckDuckGo failed")
    result = agent.fetch_news("AAPL")
    assert result == []

@patch("app.agents.sentiment_agent.GeminiClient.get_model")
def test_analyze_sentiment_json_error(mock_get_model, agent, sample_articles):
    mock_model = mock_get_model.return_value
    response_mock = MagicMock()
    response_mock.text = "invalid json"
    mock_model.generate_content.return_value = response_mock
    agent.model = mock_model

    result = agent.analyze_sentiment(sample_articles)
    assert result["overall_sentiment"] == "Neutral"
    assert result["news"] == []

@patch("app.agents.sentiment_agent.GeminiClient.get_model")
def test_analyze_sentiment_exception(mock_get_model, agent, sample_articles):
    mock_model = mock_get_model.return_value
    mock_model.generate_content.side_effect = Exception("Gemini failed")
    agent.model = mock_model

    result = agent.analyze_sentiment(sample_articles)
    assert result["overall_sentiment"] == "Neutral"
    assert result["news"] == []
