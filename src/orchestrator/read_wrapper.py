"""A wrapper agent for the RE and design agents in READ-MAS."""

from typing import Optional
from agents import (AgentBase, get_model_from)
from utils.constants import (AgentRunMode, DEFAULT_MODEL_NAME)
import time

from google.adk.agents import Agent, SequentialAgent
from utils.logger import setup_logging
from design import DesignWrapperAgent
from requirement import RequirementsWrapperAgent


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
    self._requirement_agent = RequirementsWrapperAgent(
        llm_model_name, run_mode=run_mode, rag=rag
    ).get_agent()
    self._design_agent = DesignWrapperAgent(llm_model_name, run_mode=run_mode, rag=rag).get_agent()

  def get_agent(self) -> Agent:
    return SequentialAgent(
        name="read_agent", sub_agents=[self._requirement_agent, self._design_agent]
    )


# For testing in adk web ui
run_id = str(int(time.time() * 1000))
setup_logging(run_id, "adk")
agent = ReadWrapperAgent(DEFAULT_MODEL_NAME)
root_agent = agent.get_agent()
