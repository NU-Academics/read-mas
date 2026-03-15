"""Callback functions before and after LLM and agent calls for logging."""

from typing import Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.genai import types
from loguru import logger


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
  if llm_request.contents and llm_request.contents[-1].role == "user":
    if llm_request.contents[-1].parts:
      last_user_message = llm_request.contents[-1].parts[0].text

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
