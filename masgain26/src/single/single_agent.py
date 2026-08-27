"""Single agent to specify requirements and design software."""

from typing import Optional
import time

from google.adk.agents import Agent

from agents import (AgentBase, get_model_from, add_rag_tool, get_agent_config)
from agents import (before_agent, after_agent, before_model, after_model, after_rag_tool)
from utils.constants import DEFAULT_MODEL_NAME
from prompt_templates.single_prompt import SINGLE_AGENT_SYSTEM_PROMPT
from utils.constants import AgentRunMode, ExecMode
from utils.logger import (get_run_id, setup_logging)


class SingleAgent(AgentBase):
  """Defines a single agent that both generates requirements and designs the requested software."""

  def __init__(
      self,
      llm_model_name: str,
      system_prompt: Optional[str] = SINGLE_AGENT_SYSTEM_PROMPT,
      run_mode: Optional[AgentRunMode] = AgentRunMode.MAIN,
      rag: Optional[bool] = False,
      exec_mode: Optional[ExecMode] = ExecMode.LOCAL,
      rag_source: str = "requirements",
  ):
    super().__init__(llm_model_name, system_prompt, run_mode, rag, exec_mode, rag_source)

  def get_agent(self) -> Agent:
    tools = []
    add_rag_tool(tools, self._rag, self._exec_mode, self._rag_source)

    return Agent(
        name="single_agent",
        model=get_model_from(self._llm_model_name),
        description="A single agent that generates a software design for a user's query",
        instruction=self.get_instruction,
        tools=tools,
        generate_content_config=get_agent_config(llm_model_name=self._llm_model_name),
        output_key="design_output",
        after_tool_callback=after_rag_tool if self._rag else None,
        before_agent_callback=before_agent,
        after_agent_callback=after_agent,
        before_model_callback=before_model,
        after_model_callback=after_model,
    )


# For testing in adk web ui
def __getattr__(name: str):
  if name == "root_agent":
    setup_logging(get_run_id(), "adk")
    return SingleAgent(DEFAULT_MODEL_NAME).get_agent()
  raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
