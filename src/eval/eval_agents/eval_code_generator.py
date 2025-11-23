"""Agent to generate code from outputs of design agents for evaluation."""

import sys, os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool
from eval.tools.code_generator import generate_code
from agents.agent_base import AgentBase
from agents.agent_util import get_model_from
from orchestrator.constants import DEFAULT_MODEL_NAME
from single.single_agent import SingleAgent
from eval.tools.code_generator import cleanup_code
from eval.eval_agents.prompt import EVAL_AGENT_SYSTEM_PROMPT


class EvalCodeGeneratorAgent(AgentBase):
  """Agent to generate code from outputs of design agents for evaluation."""

  def __init__(self, llm_model_name: str):
    self._llm_model_name = llm_model_name
    self._single_agent = self._get_single_agent()
    self._single_agent_tool = AgentTool(agent=self._single_agent)

  def _get_single_agent(self) -> Agent:
    """Instantiate the SingleAgent and return its underlying Agent."""
    single_agent = SingleAgent(self._llm_model_name)
    return single_agent.get_agent()

  def get_agent(self) -> Agent:
    return Agent(
        name="EvalCodeGeneratorAgent",
        model=get_model_from(self._llm_model_name),
        description=(
            "Agent to generate code using the given LLM model from outputs of design agents for"
            " evaluation."
        ),
        tools=[self._single_agent_tool, generate_code],
        instruction=EVAL_AGENT_SYSTEM_PROMPT,
    )



# for adk web test
agent = EvalCodeGeneratorAgent(DEFAULT_MODEL_NAME)
root_agent = agent.get_agent()
