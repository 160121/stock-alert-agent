import json
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
import re

from app.services.gemini_client import GeminiClient
from app.agents.technical_agent import TechnicalAgent
from app.agents.sentiment_agent import SentimentAgent
from app.agents.fundamental_agent import FundamentalAgent


class DecisionAgent:
    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.model = GeminiClient.get_model("gemini-1.5-flash")

        self.technical_agent = TechnicalAgent(ticker=self.ticker)
        self.sentiment_agent = SentimentAgent()
        self.fundamental_agent = FundamentalAgent(ticker=self.ticker)

        self.logger = logging.getLogger(__name__)
        self.executor = ThreadPoolExecutor(max_workers=3)

        # State to store agent results
        self.technical_result = None
        self.sentiment_result = None
        self.fundamental_result = None
        self.final_decision_result = None

    async def run_agents_concurrently(self):
        loop = asyncio.get_event_loop()

        tech_future = loop.run_in_executor(self.executor, self.technical_agent.run)
        sent_future = loop.run_in_executor(self.executor, lambda: self.sentiment_agent.run([self.ticker]))
        fund_future = loop.run_in_executor(self.executor, self.fundamental_agent.run)

        results = await asyncio.gather(tech_future, sent_future, fund_future)
        return results

    def aggregate_scores(self, tech_reco, overall_sentiment, fund_reco):
        score = 0

        if tech_reco.lower() == "buy":
            score += 2
        elif tech_reco.lower() == "sell":
            score -= 2

        if overall_sentiment.lower() == "positive":
            score += 1
        elif overall_sentiment.lower() == "negative":
            score -= 1

        if fund_reco.lower() in ["strong", "buy"]:
            score += 1
        elif fund_reco.lower() in ["weak", "sell"]:
            score -= 1

        self.logger.debug(
            f"Score breakdown → Tech: {tech_reco}, Sentiment: {overall_sentiment}, Fund: {fund_reco}, Final Score={score}"
        )

        if score >= 3:
            return "Strong Buy"
        elif score >= 1:
            return "Buy"
        elif score <= -3:
            return "Strong Sell"
        elif score <= -1:
            return "Sell"
        else:
            return "Hold"

    async def run(self):
        try:
            tech_result, sent_result, fund_result = await self.run_agents_concurrently()

            self.technical_result = tech_result
            self.sentiment_result = sent_result
            self.fundamental_result = fund_result

            tech_reco = tech_result.get("gemini", {}).get("recommendation", "No recommendation")
            tech_summary = tech_result.get("gemini", {}).get("summary", "No summary provided")

            sent_data = sent_result.get(self.ticker, {})
            overall_sentiment = sent_data.get("overall_sentiment", "Neutral")
            news_list = sent_data.get("news", [])

            fund_reco = fund_result.get("gemini", {}).get("recommendation", "No recommendation")
            fund_summary = fund_result.get("gemini", {}).get("summary", "No summary provided")

            self.logger.info(f"[{self.ticker}] Tech Reco={tech_reco}, Sentiment={overall_sentiment}, Fund Reco={fund_reco}")

            news_texts = [
                f"- {news.get('title', 'No title')} (Sentiment: {news.get('sentiment', 'Neutral')})"
                for news in news_list[:3]
            ]
            news_text_block = "\n".join(news_texts) if news_texts else "- No recent news available."

            # ✅ Updated Prompt
            prompt = f"""
You are a senior financial analyst. Below are the analyses for stock {self.ticker}:

Technical Analysis:
Recommendation: {tech_reco}
Summary: {tech_summary}

Sentiment Analysis:
Overall Sentiment: {overall_sentiment}
Top News:
{news_text_block}

Fundamental Analysis:
Recommendation: {fund_reco}
Summary: {fund_summary}

Weigh technical, sentiment, and fundamental analysis equally. If two or more are strong in the same direction (e.g., both "Buy" and "Positive"), prefer a decisive action (Buy or Sell) over a Hold.

Based on these, provide a final investment decision (Buy/Sell/Hold) and a brief reasoning.

Respond in JSON format:
{{"final_decision": "...", "reasoning": "..."}}
"""

            self.logger.debug(f"Prompt sent to Gemini:\n{prompt}")

            response = self.model.generate_content(prompt)
            text = response.text.strip()

            if text.startswith("```json"):
                text = text.removeprefix("```json").strip()
            if text.endswith("```"):
                text = text.removesuffix("```").strip()

            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                gemini_decision = json.loads(match.group())
            else:
                self.logger.warning(f"[{self.ticker}] Could not parse Gemini response → {text}")
                gemini_decision = {
                    "final_decision": "No decision",
                    "reasoning": "Could not parse Gemini response"
                }

            # ✅ Score-based logic
            score_decision = self.aggregate_scores(tech_reco, overall_sentiment, fund_reco)

            # ✅ Override logic — let score-based take precedence unless it's "Hold"
            final_decision = score_decision if score_decision != "Hold" else gemini_decision.get("final_decision", "Hold")

            self.final_decision_result = {
                "final_decision": final_decision,
                "score_based_decision": score_decision,
                "llm_decision": gemini_decision.get("final_decision"),
                "reasoning": gemini_decision.get("reasoning", "No reasoning provided.")
            }

            self.logger.info(f"[{self.ticker}] Final Decision={self.final_decision_result}")
            return self.final_decision_result

        except Exception as e:
            self.logger.error(f"Error running DecisionAgent: {e}", exc_info=True)
            return {
                "final_decision": "No decision",
                "reasoning": "An error occurred during decision generation.",
                "score_based_decision": "Hold",
                "llm_decision": "N/A"
            }

    def get_technical_result(self):
        return self.technical_result

    def get_sentiment_result(self):
        return self.sentiment_result

    def get_fundamental_result(self):
        return self.fundamental_result

    def get_final_decision(self):
        return self.final_decision_result
