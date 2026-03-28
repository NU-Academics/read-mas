"""Callback functions before and after LLM and agent calls for logging."""

from typing import Any, Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.adk.tools import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from loguru import logger


def after_rag_tool(
    tool: BaseTool, args: dict[str, Any], tool_context: ToolContext, tool_response: dict
) -> Optional[dict]:
  """Captures RAG tool output into session state for prompt injection."""
  logger.debug(
      f"after_rag_tool called for tool '{tool.name}' with response type"
      f" {type(tool_response).__name__}."
  )
  if tool.name == "get_requirement_examples":
    tool_context.state["rag_examples"] = tool_response
    logger.debug("Captured RAG tool output into session state for few-shot injection.")
  return None


def before_agent(callback_context: CallbackContext) -> Optional[types.Content]:
  """Logs agent input before agent call."""
  agent_name = callback_context.agent_name
  invocation_id = callback_context.invocation_id
  state = callback_context.state.to_dict()

  logger.debug(f"Entering agent {agent_name} (invocation {invocation_id}) with state {state}")
  return None


def after_agent(callback_context: CallbackContext) -> Optional[types.Content]:
  """Logs agent input after agent call."""
  agent_name = callback_context.agent_name
  invocation_id = callback_context.invocation_id
  state = callback_context.state.to_dict()

  logger.debug(f"Exiting agent {agent_name} (invocation {invocation_id}) with state {state}")
  return None


def before_model(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> Optional[LlmResponse]:
  """Callback to log input before LLM invocation."""
  agent_name = callback_context.agent_name
  last_user_message = ""
  for content in reversed(llm_request.contents or []):
    if content.role == "user" and content.parts:
      text = content.parts[0].text
      if text:
        last_user_message = text
        break

  system_prompt = llm_request.config.system_instruction or types.Content(role="system", parts=[])
  logger.debug(
      f"Invoking LLM for agent {agent_name} with system prompt {system_prompt} and user prompt"
      f" {last_user_message}."
  )

  return None


def after_model(
    callback_context: CallbackContext, llm_response: LlmResponse
) -> Optional[LlmResponse]:
  """Callback to log input and output after LLM invocation."""
  agent_name = callback_context.agent_name
  if llm_response.content and llm_response.content.parts:
    if llm_response.content.parts[0].text:
      response_text = llm_response.content.parts[0].text
      logger.debug(f"Agent {agent_name} response text: '{response_text[:100]}...'")
    elif llm_response.content.parts[0].function_call:
      logger.debug(
          f"Agent {agent_name} made a function call"
          f" '{llm_response.content.parts[0].function_call.name}'."
      )
    else:
      logger.debug(f"No text response from agent {agent_name}.")
  elif llm_response.error_message:
    logger.debug(f"Agent {agent_name} responded with error '{llm_response.error_message}'.")
  else:
    logger.debug(f"An empty LLM response from agent {agent_name}.")

  return None
