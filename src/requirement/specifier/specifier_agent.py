"""This is the last agent in the RE agent pipeline and documents the requirements using the SRS template."""

from typing import Optional
from agents import (AgentBase, get_model_from)
from utils.constants import (AgentRunMode, DEFAULT_MODEL_NAME)
import time

from google.adk.agents import Agent
from tools import save_to_file
from rag import retrieve_requirements
from utils.logger import setup_logging
from prompt_templates import SPECIFIER_AGENT_SYSTEM_PROMPT


class SpecifierAgent(AgentBase):
  """This class defines the specifier agent in the RE phase of the SDLC."""

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
    
    return Agent(
        name="collector_agent",
        model=get_model_from(self._llm_model_name),
        description=(
            "A requirements specifier agent that documents requirements using the SRS template."
        ),
        instruction=SPECIFIER_AGENT_SYSTEM_PROMPT,
        tools=tools,
        output_key="specifier_output",
    )


# For testing in adk web ui
run_id = str(int(time.time() * 1000))
setup_logging(run_id, "adk")
agent = SpecifierAgent(DEFAULT_MODEL_NAME)
root_agent = agent.get_agent()
