import yfinance as yf
import pandas as pd
import re
import json
import logging
from ddgs import DDGS

from app.services.gemini_client import GeminiClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FundamentalAgent:
    def __init__(self, ticker: str):
        self.original_ticker = ticker.strip().upper()
        self.ticker = None
        self.model = GeminiClient.get_model("gemini-1.5-flash")  # Init Gemini model once

    def resolve_symbol(self):
        # Step 1: Try direct ticker
        logger.info(f"Trying direct ticker: {self.original_ticker}")
        try:
            df = yf.Ticker(self.original_ticker).history(period="1d")
            if not df.empty:
                self.ticker = self.original_ticker
                logger.info(f"Direct ticker '{self.ticker}' works")
                return
        except Exception as e:
            logger.warning(f"Direct ticker check failed for {self.original_ticker}: {e}")

        # Step 2: Try with NSE (.NS) and BSE (.BO) suffixes
        for suffix in [".NS", ".BO"]:
            candidate = f"{self.original_ticker}{suffix}"
            try:
                logger.info(f"Trying with suffix {candidate}")
                df = yf.Ticker(candidate).history(period="1d")
                if not df.empty:
                    self.ticker = candidate
                    logger.info(f"Resolved '{self.original_ticker}' to '{self.ticker}' via suffix check")
                    return
            except Exception as e:
                logger.warning(f"Suffix check failed for {candidate}: {e}")

        # Step 3: DuckDuckGo search fallback
        logger.info(f"Direct ticker & suffixes failed, searching DuckDuckGo for symbol of '{self.original_ticker}'")
        query = f"{self.original_ticker} stock ticker yahoo finance"
        try:
            with DDGS() as ddgs:
                results = ddgs.text(query, max_results=5)
                for r in results:
                    url = r.get('url') or r.get('href') or ""
                    match = re.search(r'/quote/([A-Z0-9\.\-]+)', url)
                    if match:
                        found_symbol = match.group(1)
                        df_check = yf.Ticker(found_symbol).history(period="1d")
                        if not df_check.empty:
                            self.ticker = found_symbol
                            logger.info(f"Resolved '{self.original_ticker}' to '{self.ticker}' via DuckDuckGo")
                            return
        except Exception as e:
            logger.error(f"Error searching symbol on DuckDuckGo: {e}")

        # If everything fails
        logger.error(f"Could not resolve ticker symbol for {self.original_ticker}")
        self.ticker = None


    def fetch_data(self):
        if not self.ticker:
            self.resolve_symbol()
        if not self.ticker:
            logger.error(f"No valid ticker symbol found for {self.original_ticker}")
            return None
        try:
            t = yf.Ticker(self.ticker)
            info = t.info  # Fundamental info
            financials = {
                "market_cap": info.get("marketCap"),
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "peg_ratio": info.get("pegRatio"),
                "dividend_yield": info.get("dividendYield"),
                "beta": info.get("beta"),
                "revenue": info.get("totalRevenue"),
                "gross_profit": info.get("grossProfits"),
                "operating_margin": info.get("operatingMargins"),
                "net_income": info.get("netIncomeToCommon"),
                "debt_to_equity": info.get("debtToEquity"),
            }
            logger.info(f"Fetched fundamental data for {self.ticker}")
            return financials
        except Exception as e:
            logger.error(f"Error fetching fundamental data for {self.ticker}: {e}")
            return None

    def generate_summary_text(self, data: dict) -> str:
        lines = [f"Fundamental metrics for {self.ticker}:\n"]
        for k, v in data.items():
            lines.append(f"{k}: {v}")
        return "\n".join(lines)

    def get_gemini_recommendation(self, summary_text: str) -> dict:
        prompt = (
            "You are a financial fundamental analyst.\n"
            "Analyze the following fundamental metrics and provide a concise stock recommendation and a brief summary.\n\n"
            f"{summary_text}\n\n"
            "Respond in JSON format as:\n"
            '{"recommendation": "...", "summary": "..."}'
        )
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()

            if text.startswith("```json"):
                text = text.removeprefix("```json").strip()
            if text.endswith("```"):
                text = text.removesuffix("```").strip()

            parsed = json.loads(text)
            return parsed
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error from Gemini response: {e}\nResponse text: {response.text}")
        except Exception as e:
            logger.error(f"Error getting recommendation from Gemini: {e}")

        return {
            "recommendation": "No recommendation available.",
            "summary": "No summary available due to an error."
        }

    def run(self):
        data = self.fetch_data()
        if data:
            summary_text = self.generate_summary_text(data)
            gemini_result = self.get_gemini_recommendation(summary_text)
            return {
                "data": data,
                "gemini": gemini_result
            }
        return None
