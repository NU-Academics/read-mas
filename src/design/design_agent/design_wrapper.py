"""Wrapper agent to create a workflow of the Design agents."""

from typing import Optional
from agents import (AgentBase, get_model_from, get_agent_config)
from utils.constants import (AgentRunMode, ExecMode, DEFAULT_MODEL_NAME)
import time

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool
from utils.logger import (get_run_id, setup_logging)
from prompt_templates import DESIGN_AGENT_SYSTEM_PROMPT
from design import DesignerAgent
from design import DocumenterAgent


class DesignWrapperAgent(AgentBase):
  """This class defines the wrapper agent for the Design phase of the SDLC."""

  def __init__(
      self,
      llm_model_name: str,
      system_prompt: Optional[str] = DESIGN_AGENT_SYSTEM_PROMPT,
      run_mode: Optional[AgentRunMode] = AgentRunMode.MAIN,
      rag: Optional[bool] = True,
      exec_mode: Optional[ExecMode] = ExecMode.LOCAL,
  ):
    super().__init__(llm_model_name, system_prompt, run_mode, rag, exec_mode)
    self._designer_agent = DesignerAgent(llm_model_name, run_mode, rag, exec_mode=exec_mode).get_agent()
    self._documenter_agent = DocumenterAgent(llm_model_name, run_mode, rag, exec_mode=exec_mode).get_agent()

  def get_agent(self) -> Agent:
    tools = []

    designer_agent_tool = AgentTool(agent=self._designer_agent)
    tools.append(designer_agent_tool)
    documenter_agent_tool = AgentTool(agent=self._documenter_agent)
    tools.append(documenter_agent_tool)

    return Agent(
        name="design_agent",
        model=get_model_from(self._llm_model_name),
        description=(
            "A design wrapper agent that uses the design agent tools to generate the design."
        ),
        instruction=self._system_prompt,
        tools=tools,
        generate_content_config=get_agent_config(),
        output_key="design_output",
    )


# For testing in adk web ui
def __getattr__(name: str):
  if name == "root_agent":
    setup_logging(get_run_id(), "adk")
    return DesignWrapperAgent(DEFAULT_MODEL_NAME).get_agent()
  raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
