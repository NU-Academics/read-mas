"""Base interface for agent classes."""

from abc import ABC, abstractmethod
from typing import Optional

from google.adk.agents import Agent

from utils.constants import AgentRunMode


class AgentBase(ABC):
  """All agents use this base class."""

  @abstractmethod
  def __init__(
      self,
      llm_model_name: str,
      system_prompt: Optional[str] = None,
      run_mode: Optional[AgentRunMode] = AgentRunMode.MAIN,
      rag: Optional[bool] = False,
  ):
    """
    The agent initialization.

    Args:
      llm_model_name: The LLM model
      system_prompt: The system prompt for the agent
      run_mode: The agent run mode, e.g. main, eval, or benchmark
      rag: Whether to use the RAG tool
    """
    self._llm_model_name = llm_model_name
    self._system_prompt = system_prompt or ""
    self._run_mode = run_mode
    self._rag = rag

  @abstractmethod
  def get_agent() -> Agent:
    pass
