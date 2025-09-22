# app/core/base_agent.py
from abc import ABC, abstractmethod
import logging

class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(name)

    @abstractmethod
    def run(self, *args, **kwargs):
        """Run the agent's main task."""
        pass
