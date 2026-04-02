"""Wrapper agent to create a workflow of the RE agents."""

from typing import Optional
from agents import (add_rag_tool, AgentBase, get_model_from, get_agent_config)
from utils.constants import (AgentRunMode, ExecMode, DEFAULT_MODEL_NAME)
import time

from google.adk.agents import (Agent)
from google.adk.tools.agent_tool import AgentTool
from utils.logger import (get_run_id, setup_logging)
from prompt_templates import RE_AGENT_SYSTEM_PROMPT
from requirement import CollectorAgent
from requirement import AnalyzerAgent
from requirement import SpecifierAgent


class RequirementsWrapperAgent(AgentBase):
  """This class defines the wrapper agent for the RE phase of the SDLC."""

  def __init__(
      self,
      llm_model_name: str,
      system_prompt: Optional[str] = RE_AGENT_SYSTEM_PROMPT,
      run_mode: Optional[AgentRunMode] = AgentRunMode.MAIN,
      rag: Optional[bool] = True,
      exec_mode: Optional[ExecMode] = ExecMode.LOCAL,
  ):
    super().__init__(llm_model_name, system_prompt, run_mode, rag, exec_mode)
    self._collector_agent = CollectorAgent(
        llm_model_name, run_mode=run_mode, rag=rag, exec_mode=exec_mode
    ).get_agent()
    self._analyzer_agent = AnalyzerAgent(
        llm_model_name, run_mode=run_mode, rag=rag, exec_mode=exec_mode
    ).get_agent()
    self._specifier_agent = SpecifierAgent(
        llm_model_name, run_mode=run_mode, rag=rag, exec_mode=exec_mode
    ).get_agent()

  def get_agent(self) -> Agent:
    tools = []

    if self._rag:
      add_rag_tool(tools, self._rag, self._exec_mode)

    tools.append(AgentTool(agent=self._collector_agent))
    tools.append(AgentTool(agent=self._analyzer_agent))
    tools.append(AgentTool(agent=self._specifier_agent))

    return Agent(
        name="re_agent",
        model=get_model_from(self._llm_model_name),
        description="A requirements wrapper agent that uses RE agent tools to generate the SRS.",
        instruction=self.get_instruction,
        tools=tools,
        generate_content_config=get_agent_config(),
        output_key="requirements_output",
    )


# For testing in adk web ui
def __getattr__(name: str):
  if name == "root_agent":
    setup_logging(get_run_id(), "adk")
    return RequirementsWrapperAgent(DEFAULT_MODEL_NAME).get_agent()
  raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
