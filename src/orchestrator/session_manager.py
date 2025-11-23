"""Manages the session for the orchestrator agent."""

import uuid
from typing import Optional

from google.adk.sessions import InMemorySessionService
from google.adk.sessions.base_session_service import BaseSessionService
from google.adk.runners import Runner
from google.adk.agents import Agent
from orchestrator.constants import APP_NAME


class SessionManager:
  """Manages the session for the orchestrator agent."""

  def __init__(self):
    self._session_service = InMemorySessionService()
    self._user_id = str(uuid.uuid4())

  def get_session(self) -> BaseSessionService:
    return self._session_service

  def get_user_id(self) -> str:
    return self._user_id

  def get_session_id(self) -> str:
    return str(uuid.uuid4())

  def get_runner(self, entry_agent: Agent, app_name: Optional[str] = APP_NAME) -> Runner:
    return Runner(agent=entry_agent, app_name=app_name, session_service=self._session_service)

  async def initialize_session(
      self, entry_agent: Agent = None, app_name: Optional[str] = APP_NAME
  ) -> None:
    if entry_agent is None:
      raise ValueError("Entry agent is required")
    if app_name is None:
      raise ValueError("App name is required")
    session_id = self.get_session_id()
    await self._session_service.create_session(
        app_name=app_name, user_id=self._user_id, session_id=session_id
    )
    runner = self.get_runner(entry_agent, app_name)
    return session_id, runner, self._user_id
