import asyncio
import warnings
from typing import Optional

warnings.filterwarnings("ignore", category=FutureWarning, module="dvclive")
warnings.filterwarnings("ignore", category=FutureWarning, module="instructor")

from eval.eval_agents import EvalCodeGeneratorAgent
from eval.evaluators import (
    generate_benchmark_samples,
    AgentTrainer,
    AgentEvaluator,
    CodingBenchmarker,
)
from loguru import logger
from utils import DEFAULT_MODEL_NAME
import typer
from utils.logger import setup_logging
from utils.constants import (AgentRunMode, NUMBER_OF_TRIES)
from orchestrator import get_agent
from utils.logger import get_run_id
from dotenv import load_dotenv

# Load configs from .env file, if available.
load_dotenv()


def str_to_bool(s: str) -> bool:
  """Converts a string to a boolean value to enable using the --rag argument without being a flag."""
  s_lower = s.strip().lower()
  if s_lower in ("true", "yes", "1"):
    return True
  elif s_lower in ("false", "no", "0"):
    return False
  else:
    raise typer.BadParameter(f"'{s}' is not a valid boolean string. Use true/false/yes/no/1/0.")


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
        "single_agent",
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
    rag: str = typer.Option(
        False,
        "--rag",
        "-r",
        callback=str_to_bool,
        help="Whether to use the RAG tool",
    ),
    concurrency: int = typer.Option(
        16,
        "--concurrency",
        "-c",
        help="Maximum number of concurrent agent calls",
    ),
):
  """Generate samples for a benchmark using the evaluation coding agent. The samples are saved to a jsonl file in the data folder."""
  setup_logging(str(ctx.params["run_id"]), f"{benchmark_name}")
  logger.info(f"Starting run with ID: {run_id}")

  async def a_generate_benchmark_samples():
    """Run evaluation."""
    evaluated = get_agent(model, agent_type, AgentRunMode.CODE_BENCHMARK, rag)
    entry_agent = EvalCodeGeneratorAgent(model, evaluated).get_agent()
    await generate_benchmark_samples(
        entry_agent,
        benchmark_name,
        app_name="coding_benchmarker",
        samples_file_path=samples_file,
        num_samples=num_samples,
        concurrency=concurrency,
    )

  try:
    asyncio.run(a_generate_benchmark_samples())
  except Exception as e:
    logger.error(f"Error during execution: {str(e)}")
    print(f"[red]Error: {str(e)}[/red]")
    raise typer.Exit(1)


@app.command("code-benchmark")
def code_benchmark_agent(
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
    rag: str = typer.Option(
        "False",
        "--rag",
        "-r",
        callback=str_to_bool,
        help="Whether to use the RAG tool",
    ),
    dataset: Optional[str] = typer.Option(
        "humaneval",
        "--dataset",
        "-d",
        help="The coding benchmarking dataset: humaneval or mbpp.",
    ),
    samples_file: Optional[str] = typer.Option(
        None,
        "--samples-file",
        "-s",
        help="The sanitized samples file for the dataset.",
    ),
    experiment: bool = typer.Option(
        False,
        "--experiment",
        "-e",
        help="Whether to run a DVC experiment",
    ),
):
  setup_logging(str(ctx.params["run_id"]), "code_benchmark")

  benchmarker = CodingBenchmarker(
      run_id, agent_type, dataset, samples_file, model, rag, AgentRunMode.CODE_BENCHMARK, experiment
  )
  asyncio.run(benchmarker.benchmark())


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
    rag: str = typer.Option(
        "False",
        "--rag",
        "-r",
        callback=str_to_bool,
        help="Whether to use the RAG tool",
    ),
    no_opt: str = typer.Option(
        "False",
        "--no-opt",
        "-n",
        callback=str_to_bool,
        help="Whether to apply prompt optimization",
    ),
    experiment: bool = typer.Option(
        False,
        "--experiment",
        "-e",
        help="Whether to run a DVC experiment",
    ),
):
  setup_logging(str(ctx.params["run_id"]), "train")

  trainer = AgentTrainer(agent_type, model, rag, no_opt, experiment)
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
    rag: str = typer.Option(
        "False",
        "--rag",
        "-r",
        callback=str_to_bool,
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
    rag: str = typer.Option(
        "False",
        "--rag",
        "-r",
        callback=str_to_bool,
        help="Whether to use the RAG tool",
    ),
    experiment: bool = typer.Option(
        False,
        "--experiment",
        "-e",
        help="Whether to run a DVC experiment",
    ),
):
  setup_logging(str(ctx.params["run_id"]), "benchmark")

  benchmarker = AgentEvaluator(agent_type, model, rag, AgentRunMode.BENCHMARK, experiment)
  asyncio.run(benchmarker.eval_agent())


if __name__ == "__main__":
  app(prog_name="readmas-eval")
