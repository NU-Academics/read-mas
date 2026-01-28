"""Agent to generate code from outputs of design agents for evaluation."""

import os
import sys
from typing import Optional

from agents.agent_base import AgentBase
from agents.agent_util import get_model_from
from eval.eval_agents.prompt import EVAL_AGENT_SYSTEM_PROMPT
from eval.eval_tools import generate_code
from google.adk.agents import Agent, BaseAgent
from google.adk.tools.agent_tool import AgentTool
from utils import DEFAULT_MODEL_NAME
from single import SingleAgent
from utils.constants import AgentRunMode

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from typing import Optional
from utils.constants import AgentRunMode


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
    )


# for adk web test
single_agent = SingleAgent(DEFAULT_MODEL_NAME)
agent = EvalCodeGeneratorAgent(llm_model_name=DEFAULT_MODEL_NAME, evaluated=single_agent)
root_agent = agent.get_agent()
