"""Base interface for agent classes."""

from abc import ABC, abstractmethod
from typing import Optional

from google.adk.agents import Agent

from utils.constants import AgentRunMode


class AgentBase(ABC):
    """All agents use this base class."""

    @abstractmethod
    def __init__(self, llm_model_name: str, run_mode: Optional[AgentRunMode] = AgentRunMode.MAIN):
        self._llm_model_name = llm_model_name
        self._run_mode = run_mode

    @abstractmethod
    def get_agent() -> Agent:
        pass
