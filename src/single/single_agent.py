"""Single agent to specify requirements and design software."""

from typing import Optional
import time

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.lite_llm import LiteLlm
from google.genai.types import Content
from loguru import logger

from agents.agent_base import AgentBase
from agents.agent_util import get_model_from
from utils.constants import DEFAULT_MODEL_NAME
from prompt_templates.single_prompt import SINGLE_AGENT_SYSTEM_PROMPT
from tools.save_to_file_tool import save_to_file
from utils.constants import AgentRunMode
from rag import retrieve_requirements
from utils.logger import setup_logging

def log_single_call(callback_context: CallbackContext) -> Optional[Content]:
    design_output = callback_context.state.get("design_output")
    logger.info(f"Design output from single agent: {design_output}")


class SingleAgent(AgentBase):
    """Defines a single agent that both generates requirements and designs the requested software."""

    def __init__(self, llm_model_name: str, run_mode: Optional[AgentRunMode] = AgentRunMode.MAIN, rag: Optional[bool] = False):
        super().__init__(llm_model_name, run_mode, rag)

    def get_agent(self) -> Agent:
        tools = []
        if self._run_mode != AgentRunMode.BENCHMARK:
            tools.append(save_to_file)
        
        if self._rag:
          tools.append(retrieve_requirements)

        return Agent(
            name="single_agent",
            model=get_model_from(self._llm_model_name),
            description="A single agent that generates a software design for a user's query",
            instruction=SINGLE_AGENT_SYSTEM_PROMPT,
            tools=tools,
            output_key="design_output",
            after_agent_callback=[log_single_call],
        )


# For testing in adk web ui
run_id = str(int(time.time() * 1000))
setup_logging(run_id, 'adk')
agent = SingleAgent(DEFAULT_MODEL_NAME)
root_agent = agent.get_agent()
