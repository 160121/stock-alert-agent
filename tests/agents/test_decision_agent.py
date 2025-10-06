import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from app.agents.decision_agent import DecisionAgent

# ---------- Fixtures ----------

@pytest.fixture
def agent():
    return DecisionAgent("AAPL")

# ---------- Mocked Agent Outputs ----------

TECH_RESULT = {
    "data": "mocked_tech_data",
    "gemini": {"recommendation": "Buy", "summary": "Strong uptrend."}
}

SENT_RESULT = {
    "AAPL": {
        "overall_sentiment": "Neutral",
        "news": [
            {"title": "Apple rises", "source": "News1", "date": "2025-10-05", "url": "http://example.com", "sentiment": "Positive"}
        ]
    }
}

FUND_RESULT = {
    "data": "mocked_fund_data",
    "gemini": {"recommendation": "Buy", "summary": "Fundamentals strong."}
}

GEMINI_DECISION = {"final_decision": "Buy", "reasoning": "Strong overall indicators."}

# ---------- Tests ----------

@patch("app.agents.decision_agent.GeminiClient.get_model")
@patch.object(DecisionAgent, 'run_agents_concurrently', new_callable=AsyncMock)
def test_run_success(mock_run_agents, mock_get_model, agent):
    mock_run_agents.return_value = [TECH_RESULT, SENT_RESULT, FUND_RESULT]

    mock_model = MagicMock()
    response_mock = MagicMock()
    response_mock.text = '{"final_decision": "Buy", "reasoning": "Strong overall indicators."}'
    mock_model.generate_content.return_value = response_mock
    mock_get_model.return_value = mock_model
    agent.model = mock_model

    result = asyncio.run(agent.run())

    # Match current agent behavior
    assert result["final_decision"] == "Strong Buy"
    assert result["score_based_decision"] == "Strong Buy"
    assert result["llm_decision"] == "Buy"
    assert "reasoning" in result

@patch.object(DecisionAgent, 'run_agents_concurrently', new_callable=AsyncMock)
def test_run_gemini_parse_failure(mock_run_agents, agent):
    mock_run_agents.return_value = [TECH_RESULT, SENT_RESULT, FUND_RESULT]

    mock_model = MagicMock()
    response_mock = MagicMock()
    response_mock.text = "invalid response"
    mock_model.generate_content.return_value = response_mock
    agent.model = mock_model

    result = asyncio.run(agent.run())

    # Score-based decision dominates
    assert result["final_decision"] == "Strong Buy"
    assert result["llm_decision"] is None or result["llm_decision"] != "Strong Buy"
    assert "reasoning" in result

@patch.object(DecisionAgent, 'run_agents_concurrently', new_callable=AsyncMock)
def test_run_exception_handling(mock_run_agents, agent):
    mock_run_agents.side_effect = Exception("Concurrent execution failed")

    result = asyncio.run(agent.run())
    assert result["final_decision"] == "No decision"
    assert result["score_based_decision"] == "Hold"
    assert result["llm_decision"] == "N/A"
    assert "reasoning" in result

def test_aggregate_scores(agent):
    # Positive overall
    assert agent.aggregate_scores("Buy", "Positive", "Buy") == "Strong Buy"
    assert agent.aggregate_scores("Buy", "Neutral", "Buy") == "Strong Buy"  # matches current logic
    # Negative overall
    assert agent.aggregate_scores("Sell", "Negative", "Sell") == "Strong Sell"
    assert agent.aggregate_scores("Sell", "Neutral", "Sell") == "Strong Sell"
    # Hold case
    assert agent.aggregate_scores("Hold", "Neutral", "Hold") == "Hold"

def test_getters(agent):
    agent.technical_result = TECH_RESULT
    agent.sentiment_result = SENT_RESULT
    agent.fundamental_result = FUND_RESULT
    agent.final_decision_result = GEMINI_DECISION

    assert agent.get_technical_result() == TECH_RESULT
    assert agent.get_sentiment_result() == SENT_RESULT
    assert agent.get_fundamental_result() == FUND_RESULT
    assert agent.get_final_decision() == GEMINI_DECISION
