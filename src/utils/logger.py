import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import time

from loguru import logger


def serialize_adk_event(event: Any) -> dict:
  """
  Serialize an ADK agent event to a JSON-serializable dictionary.

  Args:
      event: The ADK event object from runner.run_async()

  Returns:
      A dictionary containing the event data
  """
  event_data = {
      "timestamp": datetime.utcnow().isoformat() + "Z",
      "event_type": type(event).__name__,
      "is_final_response": False,
      "content": None,
      "actions": None,
      "error_message": None,
      "metadata": {},
  }

  try:
    # Check if it's a final response
    if hasattr(event, "is_final_response"):
      try:
        event_data["is_final_response"] = event.is_final_response()
      except Exception:
        pass

    # Extract content
    if hasattr(event, "content") and event.content:
      try:
        content_data = {}
        if hasattr(event.content, "role"):
          content_data["role"] = str(event.content.role)
        if hasattr(event.content, "parts") and event.content.parts:
          parts = []
          for part in event.content.parts:
            try:
              part_data = {}
              if hasattr(part, "text"):
                part_data["text"] = str(part.text) if part.text else None
              if hasattr(part, "function_call"):
                part_data["function_call"] = str(part.function_call)
              parts.append(part_data)
            except Exception:
              parts.append({"error": "Failed to serialize part"})
          content_data["parts"] = parts
        event_data["content"] = content_data
      except Exception as e:
        event_data["content"] = {"error": str(e)}

    # Extract actions
    if hasattr(event, "actions") and event.actions:
      try:
        actions_data = {}
        if hasattr(event.actions, "escalate"):
          actions_data["escalate"] = bool(event.actions.escalate)
        if hasattr(event.actions, "function_call"):
          actions_data["function_call"] = str(event.actions.function_call)
        event_data["actions"] = actions_data
      except Exception as e:
        event_data["actions"] = {"error": str(e)}

    # Extract error message
    if hasattr(event, "error_message"):
      try:
        event_data["error_message"] = str(event.error_message) if event.error_message else None
      except Exception:
        pass

    # Try to extract any additional metadata
    try:
      if hasattr(event, "agent_id"):
        event_data["metadata"]["agent_id"] = str(event.agent_id)
      if hasattr(event, "session_id"):
        event_data["metadata"]["session_id"] = str(event.session_id)
      if hasattr(event, "user_id"):
        event_data["metadata"]["user_id"] = str(event.user_id)
    except Exception:
      pass

  except Exception as e:
    event_data["serialization_error"] = str(e)
    try:
      event_data["raw_event"] = str(event)
    except Exception:
      event_data["raw_event"] = "Failed to convert event to string"

  return event_data


# Thread-local storage for logging state
_logging_state = threading.local()


def log_adk_event(
    event: Any,
    query: Optional[str] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
):
  """
  Log an ADK agent event in JSON format.

  This function is designed to never raise exceptions to avoid breaking
  the main execution flow.

  Args:
      event: The ADK event object from runner.run_async()
      query: Optional query string that triggered this event
      session_id: Optional session ID
      user_id: Optional user ID
  """
  try:
    event_data = serialize_adk_event(event)

    # Add context information
    if query:
      event_data["query"] = str(query)
    if session_id:
      event_data["session_id"] = str(session_id)
    if user_id:
      event_data["user_id"] = str(user_id)

    # Log as JSON string with error handling
    try:
      json_str = json.dumps(event_data, default=str)
      logger.info(f"ADK_EVENT: {json_str}")

      # Also write directly to JSONL file if path is set
      if hasattr(_logging_state, "adk_events_path") and _logging_state.adk_events_path:
        try:
          with open(_logging_state.adk_events_path, "a", encoding="utf-8") as f:
            f.write(json_str + "\n")
        except Exception:
          # Silently fail file write
          pass
      elif hasattr(_logging_state, "path") and _logging_state.path:
        try:
          with open(_logging_state.path, "a", encoding="utf-8") as f:
            f.write(json_str + "\n")
        except Exception:
          # Silently fail file write
          pass
    except (TypeError, ValueError) as e:
      # If JSON serialization fails, log a simplified version
      event_data["json_serialization_error"] = str(e)
      logger.warning(f"ADK_EVENT: Failed to serialize event: {str(e)}")
  except Exception as e:
    # Catch all exceptions to prevent logging from breaking execution
    logger.debug(f"Failed to log ADK event: {str(e)}")


def setup_logging(run_id: str, logger_path: str):
  """Configure logging for the application."""

  log_path = (
      Path("runs") / run_id / "logs"
      if logger_path is None
      else Path("runs") / logger_path / run_id / "logs"
  )
  log_path.mkdir(parents=True, exist_ok=True)
  logger.add(log_path / "app.log", rotation="100 MB")

  # Set the ADK events file path and log path in thread-local storage
  _logging_state.log_path = log_path
  _logging_state.adk_events_path = str(log_path / "adk_events.jsonl")

  # Also persist the log path in the process environment so tools running in a different
  # thread (e.g., inside ADK tool execution) can still resolve the correct output dir.
  os.environ["READMAS_LOG_PATH"] = str(log_path)

  return log_path

def get_run_id():
  return str(int(time.time() * 1000))

def get_log_path() -> Optional[Path]:
  """Get the current log path from thread-local storage."""
  path = getattr(_logging_state, "log_path", None)
  if path is not None:
    return path

  # Fallback for tool execution contexts that do not share the caller's thread-local state.
  env_path = os.environ.get("READMAS_LOG_PATH")
  return Path(env_path) if env_path else None
