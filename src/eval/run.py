import asyncio
import json
from typing import Optional

from deepeval.synthesizer import Synthesizer
from deepeval.synthesizer.config import FiltrationConfig
from eval.eval_agents.eval_code_generator import EvalCodeGeneratorAgent
from eval.evaluators import (
    generate_benchmark_samples,
    AgentTrainer
)
from loguru import logger
from utils import DEFAULT_MODEL_NAME
from tqdm import tqdm
import typer
from utils.logger import setup_logging
from utils.constants import (AgentRunMode, NUMBER_OF_TRIES)
from orchestrator import get_agent
from utils.logger import get_run_id


app = typer.Typer(help="READ-MAS CLI for running Evals")


@app.command("generate-samples")
def generate_samples(
    benchmark_name: str,
    ctx: typer.Context,
    run_id: str = typer.Option(
        lambda: get_run_id(),
        "--run-id",
        "-i",
        help="Unique run identifier",
    ),
    model: Optional[str] = typer.Option(
        DEFAULT_MODEL_NAME, "--model", "-m", help="The LLM model name"
    ),
    agent_type: Optional[str] = typer.Option(
        "single",
        "--agent-type",
        "-t",
        help="Single or Multi-agent option.",
    ),
    samples_file: Optional[str] = typer.Option(
        None,
        "--samples-file",
        "-s",
        help=(
            "Path to an existing samples file. If provided, will resume generation from where it"
            " stopped."
        ),
    ),
    num_samples: int = typer.Option(
        NUMBER_OF_TRIES,
        "--num-samples",
        "-n",
        help="Number of samples to generate per task",
    ),
    rag: bool = typer.Option(
        False,
        "--rag",
        "-r",
        help="Whether to use the RAG tool",
    ),
):
  """Generate samples for a benchmark using the evaluation coding agent. The samples are saved to a jsonl file in the data folder."""
  log_path = setup_logging(str(ctx.params["run_id"]), f"{benchmark_name}")
  logger.info(f"Starting run with ID: {run_id}")

  async def a_generate_benchmark_samples():
    """Run evaluation."""
    evaluated = get_agent(model, agent_type, AgentRunMode.BENCHMARK, rag)
    entry_agent = EvalCodeGeneratorAgent(model, evaluated).get_agent()
    await generate_benchmark_samples(
        entry_agent,
        benchmark_name,
        app_name="agents",
        samples_file_path=samples_file,
        num_samples=num_samples,
    )

  try:
    asyncio.run(a_generate_benchmark_samples())
  except Exception as e:
    logger.error(f"Error during execution: {str(e)}")
    print(f"[red]Error: {str(e)}[/red]")
    raise typer.Exit(1)

@app.command("train")
def train_agent(
    ctx: typer.Context,
    run_id: str = typer.Option(
        lambda: get_run_id(),
        "--run-id",
        "-i",
        help="Unique run identifier",
    ),
    model: Optional[str] = typer.Option(
        DEFAULT_MODEL_NAME, "--model", "-m", help="The LLM model name"
    ),
    agent_type: Optional[str] = typer.Option(
        "single",
        "--agent-type",
        "-t",
        help="The agent to be trained.",
    ),
    rag: bool = typer.Option(
        False,
        "--rag",
        "-r",
        help="Whether to use the RAG tool",
    ),
):
  setup_logging(str(ctx.params["run_id"]), "eval")
  
  trainer = AgentTrainer(agent_type, model, rag)
  asyncio.run(trainer.train_agent())


@app.command("generate-goldens")
def generate_goldens(
    ctx: typer.Context,
    run_id: str = typer.Option(
        lambda: str(int(time.time() * 1000)),
        "--run-id",
        "-i",
        help="Unique run identifier",
    ),
    model: Optional[str] = typer.Option(
        DEFAULT_MODEL_NAME, "--model", "-m", help="The LLM model name"
    ),
):
  setup_logging(str(ctx.params["run_id"]), "eval")

  logger.info(f"Starting run with ID: {run_id}")

  with open("datasets/eval/requirement_chunks.json", "r") as rj:
    reqs = json.load(rj)

  contexts = [r["requirement"].split("|") for r in reqs]

  filtration_config = FiltrationConfig(
      critic_model="gpt-5-mini", synthetic_input_quality_threshold=0.5
  )
  synthesizer = Synthesizer(model, filtration_config=filtration_config)
  synthesizer.generate_goldens_from_contexts(contexts=contexts, max_goldens_per_context=1)
  goldens = synthesizer.synthetic_goldens
  logger.info(f"Goldens: {str(goldens)}")
  synthesizer.save_as(file_type="json", directory="data/goldens")


if __name__ == "__main__":
  app(prog_name="readmas-eval")
