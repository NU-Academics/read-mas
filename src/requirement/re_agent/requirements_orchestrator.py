"""Orchestrator agent to create a workflow of the RE agents."""

from typing import Optional
from agents import (AgentBase, get_model_from)
from utils.constants import (AgentRunMode, DEFAULT_MODEL_NAME)
import time

from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool
from utils.logger import setup_logging
from prompt_templates import RE_AGENT_SYSTEM_PROMPT
from requirement import CollectorAgent
from requirement import AnalyzerAgent
from requirement import SpecifierAgent


class RequirementsOrchestrator(AgentBase):
  """This class defines the orchestrator agent for the RE phase of the SDLC."""

  def __init__(
      self,
      llm_model_name: str,
      run_mode: Optional[AgentRunMode] = AgentRunMode.MAIN,
      rag: Optional[bool] = True,
  ):
    super().__init__(llm_model_name, run_mode, rag)
    self._collector_agent = CollectorAgent(llm_model_name, run_mode, rag)
    self._analyzer_agent = AnalyzerAgent(llm_model_name, run_mode, rag)
    self._specifier_agent = SpecifierAgent(llm_model_name, run_mode, rag)

  def get_agent(self) -> Agent:
    tools = []
    tools.append(AgentTool(agent=self._collector_agent.get_agent()))
    tools.append(AgentTool(agent=self._analyzer_agent.get_agent()))
    tools.append(AgentTool(agent=self._specifier_agent.get_agent()))

    return Agent(
        name="re_agent",
        model=get_model_from(self._llm_model_name),
        description=(
            "A requirements orchestrator agent that uses RE agent tools to generate the SRS."
        ),
        instruction=RE_AGENT_SYSTEM_PROMPT,
        tools=tools,
        output_key="requirements_output",
    )


# For testing in adk web ui
run_id = str(int(time.time() * 1000))
setup_logging(run_id, "adk")
agent = RequirementsOrchestrator(DEFAULT_MODEL_NAME)
root_agent = agent.get_agent()
