"""Base interface for agent classes."""

from abc import ABC, abstractmethod

from google.adk.agents import Agent


class AgentBase(ABC):
  """All agents use this base class."""

  @abstractmethod
  def __init__(self, llm_model_name: str):
    self._llm_model = llm_model_name

  @abstractmethod
  def get_agent() -> Agent:
    pass
