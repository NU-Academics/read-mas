import asyncio
import sys
from pathlib import Path
from typing import Optional
import typer
from rich import print
from rich.console import Console
from loguru import logger
import uuid

# Add src directory to path if running directly (not installed)
# This allows imports like 'from orchestrator.orchestrator import ...' to work
if __name__ == "__main__" or (hasattr(sys, "argv") and sys.argv[0].endswith("main.py")):
    # Get the project root (parent of src/)
    project_root = Path(__file__).parent.parent
    src_dir = project_root / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

from orchestrator.orchestrator import get_agent_response
from orchestrator.constants import DEFAULT_MODEL_NAME

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
    # Allow running as: python -m src.main run ...
    # or: python src/main.py run ...
    app(prog_name="readmas")
