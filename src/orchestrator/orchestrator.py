"""A routing agent that orchestrates the multiple RE and design agents and outputs the design."""

import asyncio
from typing import Optional

import litellm
from google.adk.agents import Agent, BaseAgent, SequentialAgent
from google.adk.runners import Runner
from google.genai import types
from loguru import logger

from .read_wrapper import ReadWrapperAgent
from design import DesignWrapperAgent
from orchestrator.constants import APP_NAME, MAX_RETRIES, RETRY_DELAY
from orchestrator.session_manager import SessionManager
from requirement import RequirementsWrapperAgent
from single import SingleAgent
from utils.constants import AgentRunMode
from utils.logger import log_adk_event

# Enable this to debug litellm
# litellm._turn_on_debug()


def get_agent(llm_model_name: str, agent_type: str, run_mode: AgentRunMode, rag: bool) -> BaseAgent:
  """Returns the agent based on the specified parameters.

  Args:
      llm_model_name: The LLM model
      agent_type: The agent type - single or multi-agent
      run_mode: The agent run mode
      rag: Whether the entry agent should use RAG

  Returns:
      The entry agent
  """
  if agent_type == "single":
    agent = SingleAgent(llm_model_name, run_mode, rag).get_agent()
  elif agent_type == "multi":
    agent = ReadWrapperAgent(llm_model_name, run_mode, rag).get_agent()
  else:
    raise ValueError(f"Invalid agent type: {agent_type}")

  return agent


async def get_agent_response(
    query: str, llm_model_name: str, agent_type: str, run_mode: AgentRunMode, rag: bool
) -> str:
  """Gets the response from the agent.

  Args:
      query: The prompt from the user requesting for a system design
      llm_model_name: The LLM model
      agent_type: The agent type - single or multi-agent
      run_mode: The agent run mode
      rag: Shows whether the agents should use RAG
  """
  entry_agent = get_agent(llm_model_name, agent_type, run_mode, rag)

  return await run_agent(query, entry_agent)


async def run_agent(
    query: str,
    entry_agent: Optional[BaseAgent] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    runner: Optional[Runner] = None,
    *,
    app_name: Optional[str] = APP_NAME,
) -> str:
  """
  Execute a single query against the supplied entry agent **inside an already‑created
  session**.  The caller is responsible for creating the session and passing the
  runner that will be reused across calls.

  Retries up to 3 times with 2 minute pauses if LLM model errors occur.
  """
  # Initialize session if needed (will be reused across retries)
  current_session_id = session_id
  current_user_id = user_id
  current_runner = runner

  if (
      current_session_id is None or current_user_id is None or current_runner is None
  ) and entry_agent is not None:
    session_manager = SessionManager()
    current_session_id, current_runner, current_user_id = await session_manager.initialize_session(
        entry_agent=entry_agent, app_name=app_name
    )
  elif entry_agent is None:
    raise ValueError("Entry agent is required")
  elif current_session_id is None or current_user_id is None or current_runner is None:
    raise ValueError("Session ID, user ID, and runner are required")

  async def _execute_agent() -> str:
    """Inner function that executes the agent logic."""
    content = types.Content(
        role="user",
        parts=[types.Part(text=query)],
    )
    response = "Sorry, no response."
    escalated_response: Optional[str] = None

    running = current_runner.run_async(
        user_id=current_user_id, session_id=current_session_id, new_message=content
    )

    try:
      async for event in running:
        log_adk_event(
            event,
            query=query,
            session_id=current_session_id,
            user_id=current_user_id,
        )

        # If an agent escalates, surface it but continue consuming the stream
        # to avoid prematurely terminating a multi-agent pipeline.
        if event.actions and event.actions.escalate:
          escalated_response = f"Agent escalated: {event.error_message or 'No specific message.'}"

        if event.is_final_response():
          if event.content and event.content.parts:
            # IMPORTANT: In a SequentialAgent, sub-agents may emit their own
            # final responses. We keep consuming events and return the *last*
            # final response, which corresponds to the overall pipeline output.
            response = event.content.parts[0].text
          else:
            # Keep consuming; a later final response may contain the actual output.
            continue
    finally:
      await running.aclose()

    return escalated_response or response

  # Retry logic for exceptions and "Sorry, no response." during agent execution
  for attempt in range(MAX_RETRIES + 1):
    try:
      response = await _execute_agent()
      # Retry if agent returns "Sorry, no response."
      if response == "Sorry, no response.":
        if attempt < MAX_RETRIES:
          logger.warning(
              f"Agent returned 'Sorry, no response.' on attempt {attempt + 1}/{MAX_RETRIES + 1}. "
              f"Retrying in {RETRY_DELAY} seconds..."
          )
          await asyncio.sleep(RETRY_DELAY)
          continue
        else:
          logger.error(
              f"Agent returned 'Sorry, no response.' for query: {query} after"
              f" {MAX_RETRIES + 1} attempts."
          )
      return response
    except Exception as e:
      if attempt < MAX_RETRIES:
        logger.warning(
            f"Error on attempt {attempt + 1}/{MAX_RETRIES + 1}: {str(e)}. "
            f"Retrying in {RETRY_DELAY} seconds..."
        )
        await asyncio.sleep(RETRY_DELAY)
      else:
        logger.error(f"Agent execution failed for query: {query} after {MAX_RETRIES + 1} attempts.")
        raise RuntimeError(
            f"Error executing agent for query: {query} after {MAX_RETRIES + 1} attempts."
        ) from e
