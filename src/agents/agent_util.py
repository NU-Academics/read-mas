"""Utility functions common for agents."""

from typing import List, Union
from utils.constants import OLLAMA_API_BASE, OLLAMA_BASE_URL

from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool import MCPToolset, StreamableHTTPConnectionParams
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

def add_rag_mcp(tools: List[any]):
  rag_toolset = MCPToolset(
    connection_params=StreamableHTTPConnectionParams(
      url=MCP_URL_RAG
    )
  )
  tools.append(rag_toolset)
