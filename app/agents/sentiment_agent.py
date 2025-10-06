# app/agents/sentiment_agent.py
import json
from typing import List, Dict, Optional
from ddgs import DDGS
from app.core.base_agent import BaseAgent
from app.services.gemini_client import GeminiClient

class SentimentAgent(BaseAgent):
    def __init__(self, symbols: List[str], max_results: int = 5, timelimit: str = "w"):
        super().__init__("SentimentAgent")
        self.original_symbols = [s.strip().upper() for s in symbols]
        self.max_results = max_results
        self.timelimit = timelimit
        self.model = GeminiClient.get_model("gemini-2.5-flash")

    def fetch_news(self, symbol: str) -> List[Dict]:
        """Fetch recent news for a given stock symbol using DuckDuckGo News."""
        try:
            with DDGS() as ddgs:
                query = f"{symbol} stock news"
                results = ddgs.news(
                    query=query,
                    timelimit=self.timelimit,
                    max_results=self.max_results,
                )
                news_list = list(results)
                self.logger.info(f"Fetched {len(news_list)} news articles for {symbol}")
                return news_list
        except Exception as e:
            self.logger.error(f"Error fetching news for {symbol}: {e}")
            return []

    def analyze_sentiment(self, articles: List[Dict]) -> Dict:
        """Analyze sentiment of news articles using Gemini."""
        if not articles:
            return {
                "overall_sentiment": "Neutral",
                "news": [],
            }

        news_texts = [
            f"Title: {a.get('title')} | Source: {a.get('source')} | Date: {a.get('date')} | URL: {a.get('url')}"
            for a in articles
        ]
        prompt = (
            "You are a financial sentiment analysis agent.\n"
            "Classify the sentiment (Positive, Negative, Neutral) for the following news:\n\n"
            + "\n".join(news_texts)
            + "\n\nReturn JSON with format:\n"
            '{"overall_sentiment": "...", "news": [{"title": "...", "source": "...", "date": "...", "url": "...", "sentiment": "..."}]}'
        )

        try:
            response = self.model.generate_content(prompt)
            cleaned_text = response.text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text.removeprefix("```json").strip()
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text.removesuffix("```").strip()

            parsed = json.loads(cleaned_text)
            return parsed
        except json.JSONDecodeError as json_err:
            self.logger.error(f"Error parsing Gemini response: {json_err}\nResponse text: {response.text}")
        except Exception as e:
            self.logger.error(f"Error analyzing sentiment: {e}")

        return {
            "overall_sentiment": "Neutral",
            "news": [],
        }

    def run(self) -> Dict[str, Dict]:
        """Run sentiment analysis for all given stock symbols."""
        results = {}
        for symbol in self.original_symbols:
            self.logger.info(f"Fetching sentiment for {symbol}")
            articles = self.fetch_news(symbol)
            sentiment = self.analyze_sentiment(articles)
            results[symbol] = sentiment
        return results
