"""Agent to generate code from outputs of design agents for evaluation."""

import os
import sys

from agents.agent_base import AgentBase
from agents.agent_util import get_model_from
from eval.eval_agents.prompt import EVAL_AGENT_SYSTEM_PROMPT
from eval.eval_tools import generate_code
from google.adk.agents import Agent, BaseAgent
from google.adk.tools.agent_tool import AgentTool
from utils import DEFAULT_MODEL_NAME
from utils.logger import (get_run_id, setup_logging)
from single import SingleAgent
from agents import (before_agent, after_agent, before_model, after_model)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class EvalCodeGeneratorAgent(AgentBase):
  """Agent to generate code from outputs of design agents for evaluation."""

  def __init__(
      self,
      llm_model_name: str,
      evaluated: BaseAgent,
  ):
    super().__init__(llm_model_name)
    self._evaluated = evaluated
    self._agent_tool = AgentTool(agent=self._evaluated)

  def get_agent(self) -> Agent:
    return Agent(
        name="EvalCodeGeneratorAgent",
        model=get_model_from(self._llm_model_name),
        description=(
            "Agent to generate code using the given LLM model from outputs of design agents for"
            " evaluation."
        ),
        tools=[self._agent_tool, generate_code],
        instruction=EVAL_AGENT_SYSTEM_PROMPT,
        before_agent_callback=before_agent,
        after_agent_callback=after_agent,
        before_model_callback=before_model,
        after_model_callback=after_model,
    )


# for adk web test
def __getattr__(name: str):
  if name == "root_agent":
    setup_logging(get_run_id(), "adk")
    single_agent = SingleAgent(DEFAULT_MODEL_NAME).get_agent()
    return EvalCodeGeneratorAgent(
        llm_model_name=DEFAULT_MODEL_NAME, evaluated=single_agent
    ).get_agent()
  raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
