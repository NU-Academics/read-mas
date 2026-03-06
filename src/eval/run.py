import asyncio
from typing import Optional

from eval.eval_agents import EvalCodeGeneratorAgent
from eval.evaluators import (
    generate_benchmark_samples,
    AgentTrainer,
    AgentEvaluator
)
from loguru import logger
from utils import DEFAULT_MODEL_NAME
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
        "single_agent",
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
    experiment: bool = typer.Option(
        False,
        "--experiment",
        "-e",
        help="Whether to run a DVC experiment",
    ),
):
  setup_logging(str(ctx.params["run_id"]), "eval")
  
  trainer = AgentTrainer(agent_type, model, rag, experiment)
  asyncio.run(trainer.train_agent())

@app.command("eval")
def eval_agent(
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
        "single_agent",
        "--agent-type",
        "-t",
        help="The agent to be evaluated.",
    ),
    rag: bool = typer.Option(
        False,
        "--rag",
        "-r",
        help="Whether to use the RAG tool",
    ),
    experiment: bool = typer.Option(
        False,
        "--experiment",
        "-e",
        help="Whether to run a DVC experiment",
    ),
):
  setup_logging(str(ctx.params["run_id"]), "eval")
  
  evaluator = AgentEvaluator(agent_type, model, rag, AgentRunMode.EVAL, experiment)
  asyncio.run(evaluator.eval_agent())

@app.command("benchmark")
def benchmark_agent(
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
        "single_agent",
        "--agent-type",
        "-t",
        help="The agent to be benchmarked.",
    ),
    rag: bool = typer.Option(
        False,
        "--rag",
        "-r",
        help="Whether to use the RAG tool",
    ),
    experiment: bool = typer.Option(
        False,
        "--experiment",
        "-e",
        help="Whether to run a DVC experiment",
    ),
):
  setup_logging(str(ctx.params["run_id"]), "eval")
  
  benchmarker = AgentEvaluator(agent_type, model, rag, AgentRunMode.BENCHMARK, experiment)
  asyncio.run(benchmarker.eval_agent())


if __name__ == "__main__":
  app(prog_name="readmas-eval")
