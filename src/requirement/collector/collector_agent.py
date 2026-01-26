"""This is the first agent in the RE agent pipeline and collects and self elicits requirements and generates raw requirements."""

from typing import Optional
from agents import (AgentBase, get_model_from)
from utils.constants import (AgentRunMode, DEFAULT_MODEL_NAME)
import time

from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.genai.types import ThinkingConfig
from tools import save_to_file
from rag import retrieve_requirements
from utils.logger import setup_logging
from prompt_templates import COLLECTOR_AGENT_SYSTEM_PROMPT
from .collector_models import CollectorOutputModel


class CollectorAgent(AgentBase):
  """This class defines the collector agent in the RE phase of the SDLC."""

  def __init__(
      self,
      llm_model_name: str,
      run_mode: Optional[AgentRunMode] = AgentRunMode.MAIN,
      rag: Optional[bool] = True,
  ):
    super().__init__(llm_model_name, run_mode, rag)

  def get_agent(self) -> Agent:
    tools = []
    if self._run_mode != AgentRunMode.BENCHMARK:
      tools.append(save_to_file)

    if self._rag:
      tools.append(retrieve_requirements)

    # Create a ThinkingConfig and planner
    thinking_config = ThinkingConfig(include_thoughts=True, thinking_budget=256)
    planner = BuiltInPlanner(thinking_config=thinking_config)

    return Agent(
        name="collector_agent",
        model=get_model_from(self._llm_model_name),
        description=(
            "A requirements collector agent that generates raw requirements from a user's query"
        ),
        instruction=COLLECTOR_AGENT_SYSTEM_PROMPT,
        planner=planner,
        tools=tools,
        output_schema=CollectorOutputModel,
        output_key="collector_output",
    )


# For testing in adk web ui
run_id = str(int(time.time() * 1000))
setup_logging(run_id, "adk")
agent = CollectorAgent(DEFAULT_MODEL_NAME)
root_agent = agent.get_agent()
