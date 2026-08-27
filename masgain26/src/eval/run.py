import asyncio
import warnings
from typing import Optional

warnings.filterwarnings("ignore", category=FutureWarning, module="dvclive")
warnings.filterwarnings("ignore", category=FutureWarning, module="instructor")

from eval.eval_agents import EvalCodeGeneratorAgent
from eval.evaluators import (
    generate_llm_samples,
    generate_benchmark_samples_directly,
    AgentTrainer,
    AgentEvaluator,
    CodingBenchmarker,
    LlmCodingBenchmarker,
)
from loguru import logger
from utils import DEFAULT_MODEL_NAME
import typer
from utils.logger import setup_logging
from utils.constants import (AgentRunMode, ExecMode, NUMBER_OF_TRIES)
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

def is_local_model(model: str) -> bool:
  return model.startswith(("ollama/", "ollama_chat/"))


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
        2,
        "--concurrency",
        "-c",
        help="Maximum number of concurrent agent calls",
    ),
    exec_mode: Optional[str] = typer.Option(
        "local",
        "--exec-mode",
        "-e",
        help="Execution mode: 'local' (inline) or 'remote' (MCP + A2A servers)",
    ),
):
  """Generate samples for a benchmark using the evaluation coding agent. The samples are saved to a jsonl file in the data folder."""
  setup_logging(str(ctx.params["run_id"]), f"{benchmark_name}")
  logger.info(f"Starting run with ID: {run_id}")

  async def a_generate_benchmark_samples():
    """Run the benchmark samples generation."""
    evaluated = get_agent(model, agent_type, AgentRunMode.CODE_BENCHMARK, rag, ExecMode(exec_mode))
    await generate_benchmark_samples_directly(
        evaluated, benchmark_name,
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
        "-x",
        help="Whether to run a DVC experiment",
    ),
    exec_mode: Optional[str] = typer.Option(
        "local",
        "--exec-mode",
        "-e",
        help="Execution mode: 'local' (inline) or 'remote' (MCP + A2A servers)",
    ),
):
  setup_logging(str(ctx.params["run_id"]), "code_benchmark")

  benchmarker = CodingBenchmarker(
      run_id, agent_type, dataset, samples_file, model, rag, AgentRunMode.CODE_BENCHMARK,
      experiment, ExecMode(exec_mode),
  )
  asyncio.run(benchmarker.benchmark())


@app.command("llm-generate-samples")
def llm_generate_samples(
    benchmark_name: str,
    ctx: typer.Context,
    run_id: str = typer.Option(
        lambda: get_run_id(),
        "--run-id",
        "-i",
        help="Unique run identifier",
    ),
    model: Optional[str] = typer.Option(
        DEFAULT_MODEL_NAME, "--model", "-m", help="The LLM model name (litellm format)"
    ),
    samples_file: Optional[str] = typer.Option(
        None,
        "--samples-file",
        "-s",
        help="Path to an existing samples file to resume from.",
    ),
    num_samples: int = typer.Option(
        NUMBER_OF_TRIES,
        "--num-samples",
        "-n",
        help="Number of samples to generate per task",
    ),
    concurrency: int = typer.Option(
        8,
        "--concurrency",
        "-c",
        help="Maximum number of concurrent LLM calls",
    ),
):
  """Generate benchmark samples by calling the LLM directly (no agents)."""
  setup_logging(str(ctx.params["run_id"]), f"{benchmark_name}_llm")
  logger.info(f"Starting LLM sample generation with run ID: {run_id}")

  try:
    asyncio.run(generate_llm_samples(model, benchmark_name, samples_file, num_samples, concurrency))
  except Exception as e:
    logger.error(f"Error during execution: {str(e)}")
    print(f"[red]Error: {str(e)}[/red]")
    raise typer.Exit(1)


@app.command("llm-benchmark")
def benchmark_coding_llm(
    ctx: typer.Context,
    run_id: str = typer.Option(
        lambda: get_run_id(),
        "--run-id",
        "-i",
        help="Unique run identifier",
    ),
    model: Optional[str] = typer.Option(
        DEFAULT_MODEL_NAME, "--model", "-m", help="The LLM model name (litellm format)"
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
        "-x",
        help="Whether to run a DVC experiment",
    ),
):
  """Evaluate a raw LLM on HumanEval/MBPP without agent orchestration."""
  setup_logging(str(ctx.params["run_id"]), "llm_benchmark")

  benchmarker = LlmCodingBenchmarker(run_id, model, dataset, samples_file, experiment)
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
        "-x",
        help="Whether to run a DVC experiment",
    ),
    exec_mode: Optional[str] = typer.Option(
        "local",
        "--exec-mode",
        "-e",
        help="Execution mode: 'local' (inline) or 'remote' (MCP + A2A servers)",
    ),
):
  setup_logging(str(ctx.params["run_id"]), "train")

  trainer = AgentTrainer(agent_type, model, rag, no_opt, experiment, ExecMode(exec_mode))
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
        "-x",
        help="Whether to run a DVC experiment",
    ),
    exec_mode: Optional[str] = typer.Option(
        "local",
        "--exec-mode",
        "-e",
        help="Execution mode: 'local' (inline) or 'remote' (MCP + A2A servers)",
    ),
):
  setup_logging(str(ctx.params["run_id"]), "eval")

  evaluator = AgentEvaluator(agent_type, model, rag, AgentRunMode.EVAL, experiment, ExecMode(exec_mode))
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
        "-x",
        help="Whether to run a DVC experiment",
    ),
    exec_mode: Optional[str] = typer.Option(
        "local",
        "--exec-mode",
        "-e",
        help="Execution mode: 'local' (inline) or 'remote' (MCP + A2A servers)",
    ),
    rag_index: Optional[str] = typer.Option(
        "requirements",
        "--rag-index",
        "-ri",
        help="RAGAS evaluation index: 'requirements' (default) or 'devbench_benchmark'",
    ),
):
  setup_logging(str(ctx.params["run_id"]), "benchmark")

  benchmarker = AgentEvaluator(
      agent_type, model, rag, AgentRunMode.BENCHMARK, experiment, ExecMode(exec_mode),
      rag_source=rag_index,
  )
  asyncio.run(benchmarker.eval_agent())


if __name__ == "__main__":
  app(prog_name="readmas-eval")
