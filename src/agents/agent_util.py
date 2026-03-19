"""Utility functions common for agents."""

from typing import List, Optional, Union
from utils.constants import OLLAMA_API_BASE, OLLAMA_BASE_URL

from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams
from google.genai.types import GenerateContentConfig
from loguru import logger

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


def add_rag_mcp(tools: List[any], rag: bool):
  if rag:
    logger.info("Adding the RAG toolset to the agent's tools list.")
    rag_toolset = McpToolset(
      connection_params=StreamableHTTPConnectionParams(
        url=MCP_URL_RAG,
        timeout=30,  # Default is 5s, too short under concurrent training load
      ),
      tool_filter=["get_requirement_examples"]
      )
    tools.append(rag_toolset)


def format_rag_few_shot(requirements) -> str:
  """Formats RAG results as few-shot examples for injection into system prompts."""
  items = _extract_rag_items(requirements)
  if not items:
    return ""
  formatted = "\n".join(f"- {item}" for item in items)
  return (
      "\nUse the following as examples of requirements or documentation snippets:\n"
      f"{formatted}\n"
  )


def _extract_rag_items(response) -> list[str]:
  """Extracts plain text requirements from MCP tool response formats."""
  if isinstance(response, list):
    return [_extract_text(item) for item in response]
  if isinstance(response, dict):
    # MCP content blocks: {"content": [{"type": "text", "text": "..."}], ...}
    if "content" in response:
      return [
          block["text"] for block in response["content"]
          if isinstance(block, dict) and block.get("type") == "text"
      ]
    # Direct result: {"result": ["...", ...]}
    if "result" in response:
      result = response["result"]
      if isinstance(result, list):
        return [_extract_text(item) for item in result]
  return [str(response)]


def _extract_text(item) -> str:
  """Extracts text from a string or MCP content block dict."""
  if isinstance(item, dict) and "text" in item:
    return item["text"]
  return str(item)


def get_agent_config():
  """Configures the agent's technical configuration attributes."""
  return GenerateContentConfig(
      temperature=0.2,
      # max_output_tokens=8192,
      top_p=0.95,
  )
