import asyncio
import time
from typing import Optional

import typer
from loguru import logger
from rich import print

from orchestrator.orchestrator import get_agent_response
from utils import DEFAULT_MODEL_NAME
from utils.constants import AgentRunMode
from utils.logger import setup_logging

app = typer.Typer(help="READ-MAS CLI for automated software design")


@app.command()
def run(
    run_id: str = typer.Option(
        lambda: str(int(time.time() * 1000)),
        "--run-id",
        "-i",
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
    rag: Optional[bool] = typer.Option(
        False,
        "--rag",
        "-r",
        help="Indicates if the agents use RAG",
    ),
):
    """Run the READ-MAS automation with specified configuration."""
    setup_logging(run_id, "cli")
    logger.info(f"Starting run with ID: {run_id}")

    try:
        logger.info(
            f"Input params: agent-type - {agent_type}, query - {query}, model - {llm_model_name}, rag -"
            f" {rag}"
        )

        response = asyncio.run(
            get_agent_response(
                query, llm_model_name, agent_type, run_mode=AgentRunMode.MAIN, rag=rag
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
