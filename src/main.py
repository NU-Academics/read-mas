import asyncio
from typing import Optional

import typer
from loguru import logger
from rich import print

from orchestrator.orchestrator import get_agent_response
from utils import DEFAULT_MODEL_NAME
from utils.constants import AgentRunMode, ExecMode
from utils.logger import get_run_id
from utils.logger import setup_logging

app = typer.Typer(help="READ-MAS CLI for automated software design")


@app.command()
def run(
    run_id: str = typer.Option(
        lambda: get_run_id(),
        "--run-id",
        "-i",
        help="Unique run identifier",
    ),
    agent_type: Optional[str] = typer.Option(
        "single_agent",
        "--agent-type",
        "-t",
        help="Single or Multi-agent option.",
    ),
    query: Optional[str] = typer.Option(
        None,
        "--query",
        "-q",
        help="User's input query",
    ),
    llm_model_name: Optional[str] = typer.Option(
        DEFAULT_MODEL_NAME,
        "--llm-model-name",
        "-m",
        help="LLM model name",
    ),
    rag: Optional[bool] = typer.Option(
        False,
        "--rag",
        "-r",
        help="Indicates if the agents use RAG",
    ),
    exec_mode: Optional[str] = typer.Option(
        "local",
        "--exec-mode",
        "-e",
        help="Execution mode: 'local' (inline, no servers needed) or 'remote' (MCP + A2A servers)",
    ),
):
  """Run the READ-MAS automation with specified configuration."""
  setup_logging(run_id, "cli")
  logger.info(f"Starting run with ID: {run_id}")

  try:
    mode = ExecMode(exec_mode)
    logger.info(
        f"Input params: agent-type - {agent_type}, query - {query}, model - {llm_model_name},"
        f" rag - {rag}, exec-mode - {mode}"
    )

    response = asyncio.run(
        get_agent_response(
            query, llm_model_name, agent_type, run_mode=AgentRunMode.MAIN, rag=rag,
            exec_mode=mode,
        )
    )
    logger.info(f"Response: {response}")
    # Also print the actual agent output to stdout (in addition to logs),
    # so users see the design/SRS content directly.
    print(response)
  except Exception as e:
    logger.error(f"Error during execution: {str(e)}")
    print(f"[red]Error: {str(e)}[/red]")
    raise typer.Exit(1)


if __name__ == "__main__":
  app(prog_name="readmas")
