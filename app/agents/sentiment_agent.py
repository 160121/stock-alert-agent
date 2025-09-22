import json
from ddgs import DDGS  
from app.services.gemini_client import GeminiClient
from app.utils.helpers import logger
class SentimentAgent():
    def __init__(self, max_results: int = 5, timelimit: str = "w"):
        """
        Args:
            max_results (int): Max news articles to fetch per symbol.
            timelimit (str): d = day, w = week, m = month.
        """
        self.max_results = max_results
        self.timelimit = timelimit
        self.model = GeminiClient.get_model("gemini-1.5-flash")

    def fetch_news(self, symbol: str):
        """Fetch recent news for a given stock symbol."""
        try:
            with DDGS() as ddgs:
                query = f"{symbol} stock news"
                results = ddgs.news(
                    query=query,
                    timelimit=self.timelimit,
                    max_results=self.max_results,
                )
                return list(results)
        except Exception as e:
            logger.error(f"Error fetching news for {symbol}: {e}")
            return []

    def analyze_sentiment(self, articles: list):
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
            logger.error(f"Error parsing Gemini response: {json_err}\nResponse text: {response.text}")
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")

        return {
            "overall_sentiment": "Neutral",
            "news": [],
        }


    def run(self, symbols: list):
        """Run sentiment analysis for given stock symbols."""
        results = {}
        for symbol in symbols:
            logger.info(f"Fetching sentiment for {symbol}")
            articles = self.fetch_news(symbol)
            sentiment = self.analyze_sentiment(articles)
            results[symbol] = sentiment
        return results
