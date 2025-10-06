from abc import ABC, abstractmethod
from app.utils.helpers import logger as app_logger

class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name
        # Use a child logger to maintain hierarchy under main "stock-alerts" logger
        self.logger = app_logger.getChild(name)

    @abstractmethod
    def run(self, *args, **kwargs):
        """Run the agent's main task."""
        pass
