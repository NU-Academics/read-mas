"""A routing agent that orchestrates the multiple RE and design agents and outputs the design."""

import asyncio
from typing import Any, Iterable, Optional

import litellm
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.genai import types
from loguru import logger

from eval.eval_agents.eval_code_generator import EvalCodeGeneratorAgent
from orchestrator.constants import APP_NAME
from orchestrator.session_manager import SessionManager
from single.single_agent import SingleAgent
from orchestrator.constants import MAX_CONCURRENCY, PAUSE, MAX_RETRIES, RETRY_DELAY
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
  max_retries = MAX_RETRIES
  retry_delay = RETRY_DELAY

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

    running = current_runner.run_async(
        user_id=current_user_id, session_id=current_session_id, new_message=content
    )

    try:
      async for event in running:
        # Log all ADK events in JSON format (errors are caught internally)
        try:
          log_adk_event(
              event,
              query=query,
              session_id=current_session_id,
              user_id=current_user_id,
          )
        except Exception:
          # Logging errors should not break execution
          pass

        if event.is_final_response():
          if event.content and event.content.parts:
            response = event.content.parts[0].text
          elif event.actions and event.actions.escalate:
            response = f"Agent escalated: {event.error_message or 'No specific message.'}"
          else:
            break
    except Exception as e:
      logger.error(f"Agent execution error for query: {query}: {str(e)}")
      raise RuntimeError(f"Error executing eval agent for query: {query}.") from e
    finally:
      await running.aclose()

    return response

  # Retry logic for exceptions during agent execution
  last_exception = None
  for attempt in range(MAX_RETRIES + 1):
    try:
      return await _execute_agent()
    except Exception as e:
      last_exception = e
      if attempt < MAX_RETRIES:
        logger.warning(
            f"Error on attempt {attempt + 1}/{MAX_RETRIES + 1}: {str(e)}. "
            f"Retrying in {RETRY_DELAY} seconds..."
        )
        await asyncio.sleep(RETRY_DELAY)
      else:
        raise RuntimeError(f"Error executing eval agent for query: {query} after {MAX_RETRIES} attempts.") from e


async def run_agent_batch(
    queries: Iterable[str],
    entry_agent: Optional[Agent] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    runner: Optional[Runner] = None,
    *,
    app_name: Optional[str] = APP_NAME,
    max_concurrency: Optional[int] = MAX_CONCURRENCY,
    pause: Optional[float] = PAUSE,
) -> list[str | Exception]:
  """
  Fire off many agent queries concurrently but **only create one
  session and one runner** for the whole batch.

  Args:
    queries: The list/iterator of query strings.
    entry_agent: The entry agent to use for the session
    session_id: The session id to associate with the session
    user_id: Optional user id to associate with the session; if omitted a
        global/placeholder value can be used.
    runner: The runner to use for the session
    app_name: The app name to associate with the session
    max_concurrency: How many queries may run in parallel.
    pause: Minimum delay between when tasks start executing (after acquiring
        semaphore). Helps to throttle the request flood if you hit rate-limits
        or want to be nice to downstream services.
  """

  # Launch workers that share the same runner & session.
  semaphore = asyncio.Semaphore(max_concurrency)

  # Rate limiting for task starts
  start_lock = asyncio.Lock()
  last_start_time: float = 0.0

  async def worker(q: str) -> str:
    # Throttle task starts if pause is specified
    if pause:
      nonlocal last_start_time
      async with start_lock:
        current_time = asyncio.get_running_loop().time()
        time_since_last_start = current_time - last_start_time
        if time_since_last_start < pause:
          await asyncio.sleep(pause - time_since_last_start)
        last_start_time = asyncio.get_running_loop().time()

    async with semaphore:
      return await run_agent(
          q,
          entry_agent=entry_agent,
          session_id=session_id,
          user_id=user_id,
          runner=runner,
          app_name=app_name,
      )

  tasks: list[asyncio.Task] = []

  try:
    for q in queries:
      tasks.append(asyncio.create_task(worker(q)))

    # Wait for all tasks to finish
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
  except Exception as e:
    # Cancel any remaining tasks and wait for them to finish
    logger.error(f"Error in run_agent_batch: {str(e)}")
    for task in tasks:
      if not task.done():
        task.cancel()
    # Wait for cancellations to complete
    await asyncio.gather(*tasks, return_exceptions=True)
    raise
