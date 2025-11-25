import asyncio
import time
from typing import Optional

from loguru import logger
from orchestrator.constants import DEFAULT_MODEL_NAME
from orchestrator.orchestrator import get_agent_response
from rich import print
import typer
from utils.logger import setup_logging

app = typer.Typer(help="READ-MAS CLI for automated software design")


@app.command()
def run(
    run_id: str = typer.Option(
        lambda: str(int(time.time() * 1000)),
        "--run-id",
        "-r",
        help="Unique run identifier",
    ),
    agent_type: Optional[str] = typer.Option(
        "single",
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
):
  """Run the READ-MAS automation with specified configuration."""
  setup_logging(run_id, "cli")
  logger.info(f"Starting run with ID: {run_id}")

  try:
    response = asyncio.run(get_agent_response(query, llm_model_name, agent_type))
    logger.info(f"Response: {response}")
  except Exception as e:
    logger.error(f"Error during execution: {str(e)}")
    print(f"[red]Error: {str(e)}[/red]")
    raise typer.Exit(1)


if __name__ == "__main__":
  app(prog_name="readmas")
