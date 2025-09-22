import yfinance as yf
import pandas as pd
import ta
import re
import json
from ddgs import DDGS
import logging

from app.services.gemini_client import GeminiClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TechnicalAgent:
    def __init__(self, ticker: str, period: str = "6mo", interval: str = "1d"):
        self.original_ticker = ticker.strip().upper()
        self.ticker = None
        self.period = period
        self.interval = interval
        self.model = GeminiClient.get_model("gemini-1.5-flash")  

    def resolve_symbol(self):
        # Step 1: Try direct ticker
        logger.info(f"Trying direct ticker: {self.original_ticker}")
        try:
            df = yf.Ticker(self.original_ticker).history(period=self.period, interval=self.interval)
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
                df = yf.Ticker(candidate).history(period=self.period, interval=self.interval)
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
                        df_check = yf.Ticker(found_symbol).history(period=self.period, interval=self.interval)
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
            df = yf.Ticker(self.ticker).history(period=self.period, interval=self.interval)
            if df.empty:
                logger.error(f"No data found for ticker {self.ticker}")
                return None
            logger.info(f"Fetched data for ticker {self.ticker}")
            return df
        except Exception as e:
            logger.error(f"Error fetching data for {self.ticker}: {e}")
            return None

    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        try:
            df['SMA_50'] = ta.trend.sma_indicator(df['Close'], window=50)
            df['EMA_20'] = ta.trend.ema_indicator(df['Close'], window=20)
            macd = ta.trend.MACD(df['Close'], window_slow=26, window_fast=12, window_sign=9)
            df['MACD'] = macd.macd()
            df['MACD_Signal'] = macd.macd_signal()
            df['RSI_14'] = ta.momentum.rsi(df['Close'], window=14)
            bb = ta.volatility.BollingerBands(df['Close'], window=20, window_dev=2)
            df['BBU_20_2.0'] = bb.bollinger_hband()
            df['BBL_20_2.0'] = bb.bollinger_lband()
            df['ATR_14'] = ta.volatility.average_true_range(df['High'], df['Low'], df['Close'], window=14)
            df['OBV'] = ta.volume.OnBalanceVolumeIndicator(df['Close'], df['Volume']).on_balance_volume()
            df['VMA_20'] = df['Volume'].rolling(window=20).mean()
            return df
        except Exception as e:
            logger.error(f"Error computing technical indicators: {e}")
            return df

    def generate_summary_text(self, df: pd.DataFrame) -> str:
        last_rows = df.tail(5)
        lines = [f"Technical indicators for {self.ticker} over last 5 days:\n"]
        for index, row in last_rows.iterrows():
            line = (
                f"Date: {index.date()}, Close: {row['Close']:.2f}, "
                f"SMA_50: {row['SMA_50']:.2f}, EMA_20: {row['EMA_20']:.2f}, "
                f"MACD: {row['MACD']:.4f}, MACD_Signal: {row['MACD_Signal']:.4f}, "
                f"RSI_14: {row['RSI_14']:.2f}, BBU_20_2.0: {row['BBU_20_2.0']:.2f}, "
                f"BBL_20_2.0: {row['BBL_20_2.0']:.2f}, ATR_14: {row['ATR_14']:.2f}, "
                f"OBV: {row['OBV']:.0f}, VMA_20: {row['VMA_20']:.0f}"
            )
            lines.append(line)
        return "\n".join(lines)

    def get_gemini_recommendation(self, summary_text: str) -> dict:
        """
        Use Gemini to generate a stock recommendation and short summary.
        Returns a dict with 'recommendation' and 'summary' keys.
        """
        prompt = (
            "You are a financial technical analyst.\n"
            "Analyze the following technical indicators and provide a concise stock recommendation and a brief summary.\n\n"
            f"{summary_text}\n\n"
            "Respond in JSON format as:\n"
            '{"recommendation": "...", "summary": "..."}'
        )
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip()

            # Clean code blocks if present
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
        df = self.fetch_data()
        if df is not None:
            df = self.compute_indicators(df)
            summary_text = self.generate_summary_text(df)
            gemini_result = self.get_gemini_recommendation(summary_text)
            return {
                "data": df.tail(15),
                "gemini": gemini_result
            }
        return None
