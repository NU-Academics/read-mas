"""This is the last agent in the Design agent pipeline and documents the design using the provided template."""

import time
from typing import Optional

from google.adk.agents import Agent

from agents import AgentBase, get_model_from
from design.designer import DesignerOutputModel
from prompt_templates import DOCUMENTER_AGENT_SYSTEM_PROMPT
from tools import save_to_file
from utils.constants import DEFAULT_MODEL_NAME, AgentRunMode
from utils.logger import setup_logging
from agents import (before_agent, after_agent, before_model, after_model)


class DocumenterAgent(AgentBase):
  """This class defines the documenter agent in the Design phase of the SDLC."""

  def __init__(
      self,
      llm_model_name: str,
      system_prompt: Optional[str] = DOCUMENTER_AGENT_SYSTEM_PROMPT,
      run_mode: Optional[AgentRunMode] = AgentRunMode.MAIN,
      rag: Optional[bool] = True,
  ):
    super().__init__(llm_model_name, system_prompt, run_mode, rag)

  def get_agent(self) -> Agent:
    tools = []
    if self._run_mode != AgentRunMode.BENCHMARK:
      tools.append(save_to_file)

    return Agent(
        name="documenter_agent",
        model=get_model_from(self._llm_model_name),
        description=(
            "A design documenter agent that specifies the system, file structure, and component"
            " designs for the requested system."
        ),
        instruction=self._system_prompt,
        tools=tools,
        input_schema=DesignerOutputModel,
        output_key="documenter_output",
        before_agent_callback=before_agent,
        after_agent_callback=after_agent,
        before_model_callback=before_model,
        after_model_callback=after_model,
    )


# For testing in adk web ui
run_id = str(int(time.time() * 1000))
setup_logging(run_id, "adk")
agent = DocumenterAgent(DEFAULT_MODEL_NAME)
root_agent = agent.get_agent()
