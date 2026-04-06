"""Utility functions common for agents."""

from typing import List, Optional, Union
from utils.constants import OLLAMA_API_BASE, OLLAMA_BASE_URL, ExecMode

from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool import McpToolset, StreamableHTTPConnectionParams
from google.genai.types import GenerateContentConfig, ThinkingConfig
from loguru import logger

from utils.constants import (MCP_URL_RAG, CONTENT_LENGTH_LARGE)


def is_gemini_model(llm_model_name: str) -> bool:
  """Returns True if the model is a native Gemini model (not wrapped via LiteLLM)."""
  return llm_model_name.startswith("gemini")


def get_planner_for(llm_model_name: str):
  """Returns a BuiltInPlanner with thinking for Gemini; None for all other models.

  BuiltInPlanner relies on Gemini's native thinking capability and is incompatible
  with LiteLLM-wrapped models (e.g. Ollama), where it causes stalls or empty responses.
  """
  if not is_gemini_model(llm_model_name):
    return None
  from google.adk.planners import BuiltInPlanner
  from google.genai.types import ThinkingConfig
  from utils.constants import THINKING_BUDGET

  thinking_config = ThinkingConfig(include_thoughts=True, thinking_budget=THINKING_BUDGET)
  return BuiltInPlanner(thinking_config=thinking_config)


def get_model_from(llm_model_name: str) -> Union[str, LiteLlm]:
  """ "Returns the model name as is for Gemini models and a LiteLlm object for others."""
  if is_gemini_model(llm_model_name):
    return llm_model_name
  elif llm_model_name.startswith("ollama"):
    import litellm

    litellm.drop_params = True

    if llm_model_name.startswith("ollama_chat/"):
      ollama_model = llm_model_name.split("/", 1)[1]
      return LiteLlm(
          model=f"openai/{ollama_model}",
          api_base=OLLAMA_API_BASE,
          timeout=120,
      )

    return LiteLlm(model=llm_model_name, api_base=OLLAMA_BASE_URL, timeout=120)
  else:
    return LiteLlm(llm_model_name)


def add_rag_tool(tools: List[any], rag: bool, exec_mode: ExecMode = ExecMode.LOCAL):
  """Attaches the RAG tool to the agent's tool list.

  In remote mode, connects to the MCP server over HTTP.
  In local mode, wraps the retriever function directly as a FunctionTool.
  """
  if not rag:
    return
  if exec_mode == ExecMode.REMOTE:
    rag_toolset = McpToolset(
        connection_params=StreamableHTTPConnectionParams(
            url=MCP_URL_RAG,
            timeout=30,  # Default is 5s, too short under concurrent training load
        ),
        tool_filter=["get_requirement_examples"],
    )
    tools.append(rag_toolset)
  else:
    from google.adk.tools import FunctionTool
    from rag.retriever import retrieve_requirements

    def get_requirement_examples(query: str) -> list[str]:
      """Retrieve relevant requirement examples from the local knowledge base."""
      return retrieve_requirements(query)

    tools.append(FunctionTool(get_requirement_examples))


def format_rag_few_shot(requirements) -> str:
  """Formats RAG results as few-shot examples for injection into system prompts."""
  items = _extract_rag_items(requirements)
  if not items:
    return ""
  formatted = "\n".join(f"- {item}" for item in items)
  return (
      f"\nUse the following as examples of requirements or documentation snippets:\n{formatted}\n"
  )


def _extract_rag_items(response) -> list[str]:
  """Extracts plain text requirements from MCP tool response formats."""
  if isinstance(response, list):
    return [_extract_text(item) for item in response]
  if isinstance(response, dict):
    # MCP content blocks: {"content": [{"type": "text", "text": "..."}], ...}
    if "content" in response:
      return [
          block["text"]
          for block in response["content"]
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


def get_agent_config(
    max_output_tokens: int = CONTENT_LENGTH_LARGE,
    thinking_budget: Optional[int] = None,
):
  """Configures the agent's technical configuration attributes."""
  return GenerateContentConfig(
      temperature=0.2,
      max_output_tokens=max_output_tokens,
      thinking_config=ThinkingConfig(thinking_budget=thinking_budget) if thinking_budget is not None else None,
  )
