"""Single agent to specify requirements and design software."""

from typing import Optional

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.lite_llm import LiteLlm
from google.genai.types import Content
from loguru import logger

from agents.agent_base import AgentBase
from agents.agent_util import get_model_from
from orchestrator.constants import DEFAULT_MODEL_NAME
from prompt_templates.single_prompt import SINGLE_AGENT_SYSTEM_PROMPT
from tools import save_to_file
from utils.constants import AgentRunMode


def log_single_call(callback_context: CallbackContext) -> Optional[Content]:
    design_output = callback_context.state.get("design_output")
    logger.info(f"Design output from single agent: {design_output}")


class SingleAgent(AgentBase):
    """Defines a single agent that both generates requirements and designs the requested software."""

    def __init__(self, llm_model_name: str, run_mode: AgentRunMode = AgentRunMode.MAIN):
        """Initializes the single RE and design agent.

        Args:
            llm_model_name: The selected LLM model for the agent
            run_mode: The agent run mode
        """
        super().__init__(llm_model_name, run_mode)

    def get_agent(self) -> Agent:
        tools = []
        if self._run_mode != AgentRunMode.BENCHMARK:
            tools.append(save_to_file)

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
agent = SingleAgent(DEFAULT_MODEL_NAME)
root_agent = agent.get_agent()
