# app/services/gemini_client.py

import google.generativeai as genai
from app.utils.config import GEMINI_API_KEY, validate
from app.utils.helpers import logger

class GeminiClient:
    _initialized = False


    @staticmethod
    def init():
        """Initialize Gemini API client only once."""
        if not GeminiClient._initialized:
            validate()
            genai.configure(api_key=GEMINI_API_KEY)
            GeminiClient._initialized = True
            logger.info("✅ Gemini API client initialized.")

    @staticmethod
    def get_model(model_name="gemini-1.5-flash"):
        """Get a generative model instance."""
        GeminiClient.init()
        return genai.GenerativeModel(model_name)
