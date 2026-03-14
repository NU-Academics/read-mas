"""An MCP server to expose the RAG retriever as a shared tool."""

from mcp.server.fastmcp import FastMCP
from pydantic import Field
from typing import Optional, List

from rag.retriever import retrieve_requirements

mcp = FastMCP("READ-MAS RAG server", host="0.0.0.0", port=8001)

@mcp.tool(
  description="Returns example functional and non-functional requirements matching the user's query."
)
def get_requirement_examples(query: str = Field(description="The user query requesting for an application design.")) -> Optional[List[str]]:
  """Retrieve sample requirements for the given query.
  
  Args:
    query: The input to the agent
    
  Returns:
    An optional list of requirements
  """
  return retrieve_requirements(query)

if __name__ == "__main__":
  mcp.run(transport="streamable-http")