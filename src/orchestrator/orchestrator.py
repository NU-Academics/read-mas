"""A routing agent that orchestrates the multiple RE and design agents and outputs the design."""

from google.adk.agents import Agent

from src.single.single_agent import SingleAgent
from google.genai import types

from src.orchestrator.session_manager import SessionManager
from src.orchestrator.constants import APP_NAME

session_manager = SessionManager()
session_service = session_manager.get_session()
user_id = session_manager.get_user_id()


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


async def run_agent(query: str, entry_agent: Agent):
    """Runs the entry agent.

    Args:
      entry_agent: The entry agent to run
      query: The user's input message
    """
    runner = session_manager.get_runner(entry_agent)
    content = types.Content(role="user", parts=[types.Part(text=query)])
    session_id = session_manager.get_session_id()
    response = "Sorry, no response."

    # Ensure the session exists before running the agent
    await session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )

    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=content
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                response = event.content.parts[0].text
            elif event.actions and event.actions.escalate:
                response = (
                    f"Agent escalated: {event.error_message or 'No specific message.'}"
                )
            break
    return response
