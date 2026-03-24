"""Single agent to specify requirements and design software."""

from typing import Optional
import time

from google.adk.agents import Agent

from agents import (AgentBase, get_model_from, add_rag_mcp, get_agent_config)
from agents import (before_agent, after_agent, before_model, after_model, after_rag_tool)
from utils.constants import DEFAULT_MODEL_NAME
from prompt_templates.single_prompt import SINGLE_AGENT_SYSTEM_PROMPT
from utils.constants import AgentRunMode
from utils.logger import setup_logging


class SingleAgent(AgentBase):
  """Defines a single agent that both generates requirements and designs the requested software."""

  def __init__(
      self,
      llm_model_name: str,
      system_prompt: Optional[str] = SINGLE_AGENT_SYSTEM_PROMPT,
      run_mode: Optional[AgentRunMode] = AgentRunMode.MAIN,
      rag: Optional[bool] = False,
  ):
    super().__init__(llm_model_name, system_prompt, run_mode, rag)

  def get_agent(self) -> Agent:
    tools = []
    add_rag_mcp(tools, self._rag)

    return Agent(
        name="single_agent",
        model=get_model_from(self._llm_model_name),
        description="A single agent that generates a software design for a user's query",
        instruction=self.get_instruction,
        tools=tools,
        generate_content_config=get_agent_config(),
        output_key="design_output",
        after_tool_callback=after_rag_tool if self._rag else None,
        before_agent_callback=before_agent,
        after_agent_callback=after_agent,
        before_model_callback=before_model,
        after_model_callback=after_model,
    )


# For testing in adk web ui
run_id = str(int(time.time() * 1000))
setup_logging(run_id, "adk")
agent = SingleAgent(DEFAULT_MODEL_NAME)
root_agent = agent.get_agent()
