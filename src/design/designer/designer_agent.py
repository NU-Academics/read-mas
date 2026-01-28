"""This is the first agent in the Design agent pipeline and generates the system and component design for the given requirements."""

from typing import Optional
from agents import (AgentBase, get_model_from)
from utils.constants import (AgentRunMode, DEFAULT_MODEL_NAME)
import time

from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from google.genai.types import ThinkingConfig
from utils.logger import setup_logging
from prompt_templates import DESIGNER_AGENT_SYSTEM_PROMPT
from .designer_models import DesignerOutputModel

class DesignerAgent(AgentBase):
  """This class defines the designer agent in the Design phase of the SDLC."""

  def __init__(
      self,
      llm_model_name: str,
      run_mode: Optional[AgentRunMode] = AgentRunMode.MAIN,
      rag: Optional[bool] = True,
  ):
    super().__init__(llm_model_name, run_mode, rag)

  def get_agent(self) -> Agent:
    thinking_config = ThinkingConfig(include_thoughts=True, thinking_budget=256)
    planner = BuiltInPlanner(thinking_config=thinking_config)

    return Agent(
        name="designer_agent",
        model=get_model_from(self._llm_model_name),
        description=(
            "A designer agent that generates the system and component design for the given requirements."
        ),
        instruction=DESIGNER_AGENT_SYSTEM_PROMPT,
        planner=planner,
        output_schema=DesignerOutputModel,
        output_key="designer_output",
    )


# For testing in adk web ui
run_id = str(int(time.time() * 1000))
setup_logging(run_id, "adk")
agent = DesignerAgent(DEFAULT_MODEL_NAME)
root_agent = agent.get_agent()
