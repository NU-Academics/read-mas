import asyncio
import typer
from pathlib import Path
from typing import Optional, List, Dict, Any, Set, Union
from rich import print
from rich.table import Table
from rich.console import Console
from loguru import logger
import uuid
from src.orchestrator.orchestrator import get_agent_response
from src.orchestrator.constants import DEFAULT_MODEL_NAME

app = typer.Typer(help="READ-MAS CLI for automated software design")


def setup_logging(run_id: str):
    """Configure logging for the application."""
    log_path = Path("runs") / run_id / "logs"
    log_path.mkdir(parents=True, exist_ok=True)
    logger.add(log_path / "app.log", rotation="100 MB")


@app.command()
def run(
    run_id: str = typer.Option(
        str(uuid.uuid4()), "--run-id", "-r", help="Unique run identifier"
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
    setup_logging(run_id)
    logger.info(f"Starting run with ID: {run_id}")

    try:
        response = asyncio.run(get_agent_response(query, llm_model_name, agent_type))
        logger.info(f"Response: {response}")
        print(response)

    except Exception as e:
        logger.error(f"Error during execution: {str(e)}")
        print(f"[red]Error: {str(e)}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
