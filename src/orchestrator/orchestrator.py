"""A routing agent that orchestrates the multiple RE and design agents and outputs the design."""

import asyncio
from typing import Optional

import litellm
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.genai import types
from loguru import logger

from orchestrator.constants import APP_NAME, MAX_RETRIES, RETRY_DELAY
from orchestrator.session_manager import SessionManager
from single.single_agent import SingleAgent
from utils.logger import log_adk_event

# Enable this to debug litellm
# litellm._turn_on_debug()


async def get_agent_response(query: str, llm_model_name: str, agent_type: str) -> str:
    """Gets the response from the agent."""
    if agent_type == "single":
        return await run_single_agent(query, llm_model_name)
    elif agent_type == "multi":
        ...
        # return await run_multi_agent(query, llm_model_name)
    else:
        raise ValueError(f"Invalid agent type: {agent_type}")


async def run_single_agent(query: str, llm_model_name: str):
    """Runs the single agent."""
    single_agent = SingleAgent(llm_model_name)
    return await run_agent(query, single_agent.get_agent())


# async def run_multi_agent(query: str, llm_model_name: str):
#     """Runs the multi agent."""
#     multi_agent = MultiAgent(llm_model_name)
#     return await run_agent(query, multi_agent.get_agent())


async def run_agent(
    query: str,
    entry_agent: Optional[Agent] = None,
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
        current_session_id, current_runner, current_user_id = (
            await session_manager.initialize_session(entry_agent=entry_agent, app_name=app_name)
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

                if event.is_final_response():
                    if event.content and event.content.parts:
                        response = event.content.parts[0].text
                        break
                    elif event.actions and event.actions.escalate:
                        response = (
                            f"Agent escalated: {event.error_message or 'No specific message.'}"
                        )
                        break
                    else:
                        break
        finally:
            await running.aclose()

        return response

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
                        f"Agent returned 'Sorry, no response.' for query: {query} after {MAX_RETRIES + 1} attempts."
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
                logger.error(
                    f"Agent execution failed for query: {query} after {MAX_RETRIES + 1} attempts."
                )
                raise RuntimeError(
                    f"Error executing agent for query: {query} after {MAX_RETRIES + 1} attempts."
                ) from e
