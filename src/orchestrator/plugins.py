"""Custom ADK plugins for READ-MAS."""

from typing import Any, Optional

from google.adk.plugins import ReflectAndRetryToolPlugin
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

NO_RESPONSE_ERROR_TYPE = "agent_no_response"


class ReadMasRetryPlugin(ReflectAndRetryToolPlugin):
  """ReflectAndRetryToolPlugin extended to detect empty/no-response agent tool results.

  When an agent produces no content, the agent returns ''
  (empty string). This subclass surfaces that as a retryable error so the LLM
  receives structured reflection guidance and retries the agent call.
  """

  async def extract_error_from_result(
      self,
      *,
      tool: BaseTool,
      tool_args: dict[str, Any],
      tool_context: ToolContext,
      result: Any,
  ) -> Optional[Any]:
    if isinstance(result, str) and not result.strip():
      return {"error": NO_RESPONSE_ERROR_TYPE, "message": "Agent returned no response."}
    if isinstance(result, dict) and result.get("error") == NO_RESPONSE_ERROR_TYPE:
      return result
    return None
