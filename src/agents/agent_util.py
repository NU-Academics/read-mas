"""Utility functions common for agents."""

from typing import List, Optional, Union
from utils.constants import OLLAMA_API_BASE, OLLAMA_BASE_URL

from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool import MCPToolset, StreamableHTTPConnectionParams
from google.genai.types import GenerateContentConfig

from utils.constants import MCP_URL_RAG


def get_model_from(llm_model_name: str) -> Union[str, LiteLlm]:
  """ "Returns the model name as is for Gemini models and a LiteLlm object for others."""
  if llm_model_name.startswith("gemini"):
    return llm_model_name
  elif llm_model_name.startswith("ollama"):
    import litellm

    litellm.drop_params = True

    if llm_model_name.startswith("ollama_chat/"):
      ollama_model = llm_model_name.split("/", 1)[1]
      return LiteLlm(
          model=f"openai/{ollama_model}",
          api_base=OLLAMA_API_BASE,
      )

    return LiteLlm(model=llm_model_name, api_base=OLLAMA_BASE_URL)
  else:
    return LiteLlm(llm_model_name)


def add_rag_mcp(tools: List[any], rag: Optional[bool] = False):
  if rag:
    rag_toolset = MCPToolset(connection_params=StreamableHTTPConnectionParams(url=MCP_URL_RAG))
    tools.append(rag_toolset)


def get_agent_config():
  """Configures the agent's technical configuration attributes."""
  return GenerateContentConfig(
      temperature=0.2,
      # max_output_tokens=8192,
      top_p=0.95,
  )
