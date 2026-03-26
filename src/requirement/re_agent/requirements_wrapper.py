"""Wrapper agent to create a workflow of the RE agents."""

from typing import Optional
from agents import (add_rag_mcp, AgentBase, get_model_from, get_agent_config)
from utils.constants import (AgentRunMode, DEFAULT_MODEL_NAME)
import time

from google.adk.agents import (Agent)
from google.adk.tools.agent_tool import AgentTool
from utils.logger import setup_logging
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
  ):
    super().__init__(llm_model_name, system_prompt, run_mode, rag)
    self._collector_agent = CollectorAgent(llm_model_name, run_mode=run_mode, rag=rag).get_agent()
    self._analyzer_agent = AnalyzerAgent(llm_model_name, run_mode=run_mode, rag=rag).get_agent()
    self._specifier_agent = SpecifierAgent(llm_model_name, run_mode=run_mode, rag=rag).get_agent()

  def get_agent(self) -> Agent:
    tools = []

    if self._rag:
      add_rag_mcp(tools, self._rag)

    tools.append(AgentTool(agent=self._collector_agent))
    tools.append(AgentTool(agent=self._analyzer_agent))
    tools.append(AgentTool(agent=self._specifier_agent))

    return Agent(
        name="re_agent",
        model=get_model_from(self._llm_model_name),
        description="A requirements wrapper agent that uses RE agent tools to generate the SRS.",
        instruction=self._system_prompt,
        tools=tools,
        generate_content_config=get_agent_config(),
        output_key="requirements_output",
    )


# For testing in adk web ui
run_id = str(int(time.time() * 1000))
setup_logging(run_id, "adk")
agent = RequirementsWrapperAgent(DEFAULT_MODEL_NAME)
root_agent = agent.get_agent()
