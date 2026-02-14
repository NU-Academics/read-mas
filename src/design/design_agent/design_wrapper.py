"""Wrapper agent to create a workflow of the Design agents."""

from typing import Optional
from agents import (AgentBase, get_model_from)
from utils.constants import (AgentRunMode, DEFAULT_MODEL_NAME)
import time

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool
from utils.logger import setup_logging
from prompt_templates import DESIGN_AGENT_SYSTEM_PROMPT
from design import DesignerAgent
from design import DocumenterAgent
from tools import save_to_file


class DesignWrapperAgent(AgentBase):
  """This class defines the wrapper agent for the Design phase of the SDLC."""

  def __init__(
      self,
      llm_model_name: str,
      system_prompt: Optional[str] = DESIGN_AGENT_SYSTEM_PROMPT,
      run_mode: Optional[AgentRunMode] = AgentRunMode.MAIN,
      rag: Optional[bool] = True,
  ):
    super().__init__(llm_model_name, system_prompt, run_mode, rag)
    self._designer_agent = DesignerAgent(llm_model_name, run_mode, rag).get_agent()
    self._documenter_agent = DocumenterAgent(llm_model_name, run_mode, rag).get_agent()

  def get_agent(self) -> Agent:
    tools = []

    designer_agent_tool = AgentTool(agent=self._designer_agent)
    tools.append(designer_agent_tool)
    documenter_agent_tool = AgentTool(agent=self._documenter_agent)
    tools.append(documenter_agent_tool)

    if self._run_mode != AgentRunMode.BENCHMARK:
      tools.append(save_to_file)

    return Agent(
        name="design_agent",
        model=get_model_from(self._llm_model_name),
        description=(
            "A design wrapper agent that uses the design agent tools to generate the design."
        ),
        instruction=self._system_prompt,
        tools=tools,
        output_key="design_output",
    )


# For testing in adk web ui
run_id = str(int(time.time() * 1000))
setup_logging(run_id, "adk")
agent = DesignWrapperAgent(DEFAULT_MODEL_NAME)
root_agent = agent.get_agent()
