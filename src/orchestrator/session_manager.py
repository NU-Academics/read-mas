"""Manages the session for the orchestrator agent."""

import uuid
from google.adk.sessions import InMemorySessionService
from google.adk.sessions.base_session_service import BaseSessionService
from google.adk.runners import Runner
from google.adk.agents import Agent
from src.orchestrator.constants import APP_NAME

class SessionManager:
  """Manages the session for the orchestrator agent."""

  def __init__(self):
      self._session_service = InMemorySessionService()
      self._user_id = "test_user"

  def get_session(self)->BaseSessionService:
      return self._session_service

  def get_user_id(self)->str:
      return self._user_id

  def get_session_id(self)->str:
      return str(uuid.uuid4())

  def get_runner(self, entry_agent: Agent)->Runner:
    return Runner(agent=entry_agent, app_name=APP_NAME, session_service=self._session_service)