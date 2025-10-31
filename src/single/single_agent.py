"""Single agent to specify requirements and design software. """
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from src.agents.agent_base import AgentBase
from src.agents.agent_util import get_model_from


SYSTEM_PROMPT = """You are an expert software requirements and design architect. 
Create an SRS and then a system design for an application requested by the user."""

class SingleAgent(AgentBase):
    """Defines a single agent that both generates requirements and designs the requested software."""
    
    def __init__(self, llm_model_name: str):
        """Initializes the single RE and design agent.
        
        Args:
            llm_model_name: The selected LLM model for the agent
        """
        self._llm_model_name = llm_model_name
        
    def get_agent(self) -> Agent:
        return Agent(
            name="single_agent",
            model=get_model_from(self._llm_model_name),
            description="A single agent that generates both the requirements and software design for a user's query",
            instruction=SYSTEM_PROMPT
        )

    def get_system_prompt(self):
        return SYSTEM_PROMPT

# For testing in adk web ui
#agent = SingleAgent(DEFAULT_MODEL_NAME)
#root_agent = agent.get_agent()