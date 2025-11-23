import asyncio
from typing import Optional
import time

import typer
from loguru import logger

from orchestrator.constants import DEFAULT_MODEL_NAME
from orchestrator.session_manager import SessionManager
from orchestrator.orchestrator import run_agent_batch
from utils.logger import setup_logging
from eval.eval_agents.eval_code_generator import EvalCodeGeneratorAgent
from deepeval.synthesizer import Synthesizer
from deepeval.synthesizer.config import FiltrationConfig
from eval.evaluators.benchmark_evals.benchmark_evaluator import (
    generate_benchmark_samples,
)
from tqdm import tqdm


app = typer.Typer(help="READ-MAS CLI for running Evals")


@app.command("generate-samples")
def generate_samples(
    benchmark_name: str,
    ctx: typer.Context,
    run_id: str = typer.Option(
        lambda: str(int(time.time() * 1000)),
        "--run-id",
        "-r",
        help="Unique run identifier",
    ),
    model: Optional[str] = typer.Option(
        DEFAULT_MODEL_NAME, "--model", "-m", help="The LLM model name"
    ),
):
  """Generate samples for a benchmark using the evaluation coding agent. The samples are saved to a jsonl file in the data folder."""
  setup_logging(str(ctx.params["run_id"]), f"{benchmark_name}")
  logger.info(f"Starting run with ID: {run_id}")

  async def a_generate_benchmark_samples():
    """Run evaluation."""
    entry_agent = EvalCodeGeneratorAgent(model).get_agent()
    await generate_benchmark_samples(entry_agent, benchmark_name, app_name="agents")

  try:
    asyncio.run(a_generate_benchmark_samples())
  except Exception as e:
    logger.error(f"Error during execution: {str(e)}")
    print(f"[red]Error: {str(e)}[/red]")
    raise typer.Exit(1)


@app.command("generate-goldens")
def generate_goldens(
    ctx: typer.Context,
    run_id: str = typer.Option(
        lambda: str(int(time.time() * 1000)),
        "--run-id",
        "-r",
        help="Unique run identifier",
    ),
    model: Optional[str] = typer.Option(
        DEFAULT_MODEL_NAME, "--model", "-m", help="The LLM model name"
    ),
):
  setup_logging(str(ctx.params["run_id"]), "eval")

  logger.info(f"Starting run with ID: {run_id}")

  filtration_config = FiltrationConfig(
      critic_model="gpt-5-mini", synthetic_input_quality_threshold=0.5
  )
  synthesizer = Synthesizer(model, filtration_config=filtration_config)
  synthesizer.generate_goldens_from_docs(
      document_paths=[
          "/Users/mesfinbt/src/dissertation/rSDE-Bench/inference/docs/VolunteerMatch.md",
          "/Users/mesfinbt/src/dissertation/rSDE-Bench/inference/docs/VirtualWellnessRetreats.md",
          "/Users/mesfinbt/src/dissertation/rSDE-Bench/inference/docs/VirtualBookPublishing.md",
      ],
  )
  goldens = synthesizer.synthetic_goldens
  logger.info(f"Goldens: {str(goldens)}")
  synthesizer.save_as(file_type="json", directory="data")


if __name__ == "__main__":
  app(prog_name="readmas-eval")
