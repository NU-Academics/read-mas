"""An MCP server to expose the RAG retriever as a shared tool."""

import json
from mcp.server.fastmcp import FastMCP
from typing import Optional, List

from .retriever import retrieve_requirements

mcp_server = FastMCP("READ-MAS RAG server", host="0.0.0.0", port=8001)

@mcp_server.tool()
def get_requirement_examples(query: str) -> Optional[List[str]]:
  """Retrieve sample requirements for the given query.
  
  Args:
    query: The input to the agent
    
  Returns:
    An optional list of requirements
  """
  return retrieve_requirements(query)

if __name__ == "__main__":
  mcp_server.run(transport="streamable-http")