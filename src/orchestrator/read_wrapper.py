"""A wrapper agent for the RE and design agents in READ-MAS."""

from typing import Optional
from agents import (
    AgentBase,
)
from dotenv import load_dotenv
import os
import time

import warnings

warnings.filterwarnings("ignore", category=UserWarning, message=".*RemoteA2aAgent.*")

from google.adk.agents import Agent, SequentialAgent
from google.adk.agents.remote_a2a_agent import AGENT_CARD_WELL_KNOWN_PATH
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from utils.logger import (get_run_id, setup_logging)
from design import DesignWrapperAgent
from design.design_agent import design_agent_card
from requirement import RequirementsWrapperAgent
from requirement.re_agent import re_agent_card
from utils.constants import (AgentRunMode, DEFAULT_MODEL_NAME, DESIGN_A2A_PORT, RE_A2A_PORT)

# Load configs from .env file, if available.
load_dotenv()


def _agent_env_config() -> tuple[str, AgentRunMode, bool]:
  """Read A2A agent config from environment variables."""
  model = os.getenv("READMAS_MODEL", DEFAULT_MODEL_NAME)
  run_mode = AgentRunMode[os.getenv("READMAS_RUN_MODE", "MAIN")]
  rag = os.getenv("READMAS_RAG", "false").lower() == "true"
  return model, run_mode, rag


def _build_re_a2a_app():
  """The requirements A2A agent."""
  model, run_mode, rag = _agent_env_config()
  setup_logging(get_run_id(), run_mode.value)
  agent = RequirementsWrapperAgent(model, run_mode=run_mode, rag=rag).get_agent()
  return to_a2a(agent, port=RE_A2A_PORT, agent_card=re_agent_card)


def _build_design_a2a_app():
  """The design A2A agent."""
  model, run_mode, rag = _agent_env_config()
  setup_logging(get_run_id(), run_mode.value)
  agent = DesignWrapperAgent(model, run_mode=run_mode, rag=rag).get_agent()
  return to_a2a(agent, port=DESIGN_A2A_PORT, agent_card=design_agent_card)


# Lazy load the A2A apps and root_agent (for testing with ADK Web) to avoid their creation during the import of ReadWrapperAgent.
_agent_cache: dict = {}


def __getattr__(name: str):
  if name == "re_a2a_app":
    if name not in _agent_cache:
      _agent_cache[name] = _build_re_a2a_app()
    return _agent_cache[name]
  if name == "design_a2a_app":
    if name not in _agent_cache:
      _agent_cache[name] = _build_design_a2a_app()
    return _agent_cache[name]
  if name == "root_agent":
    if name not in _agent_cache:
      setup_logging(get_run_id(), "adk")
      _agent_cache[name] = ReadWrapperAgent(DEFAULT_MODEL_NAME).get_agent()
    return _agent_cache[name]
  raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


class ReadWrapperAgent(AgentBase):
  """This class defines the wrapper agent for the RE and design phases of the SDLC."""

  def __init__(
      self,
      llm_model_name: str,
      system_prompt: Optional[str] = None,
      run_mode: Optional[AgentRunMode] = AgentRunMode.MAIN,
      rag: Optional[bool] = False,
  ):
    super().__init__(llm_model_name, system_prompt=system_prompt, run_mode=run_mode, rag=rag)

  def get_agent(self) -> Agent:
    re_remote = RemoteA2aAgent(
        name="re_agent",
        agent_card=re_agent_card,
    )
    design_remote = RemoteA2aAgent(
        name="design_agent",
        agent_card=design_agent_card,
    )
    return SequentialAgent(
        name="read_agent",
        sub_agents=[re_remote, design_remote],
    )
