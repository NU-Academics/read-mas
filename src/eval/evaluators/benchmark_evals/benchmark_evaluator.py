from evalplus.evaluate import evaluate
from evalplus.data.humaneval import get_human_eval
from evalplus.data.mbpp import get_mbpp
from typing import Optional
from google.adk.agents import Agent
from google.adk.runners import Runner
from orchestrator.orchestrator import run_agent_batch
from orchestrator.constants import APP_NAME
from loguru import logger
import json
from pathlib import Path
import time


async def generate_benchmark_samples(
    entry_agent: Agent,
    benchmark_name: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    runner: Optional[Runner] = None,
    app_name: Optional[str] = APP_NAME,
):
  """Generate samples for a benchmark using the evaluation coding agent. The samples are saved to a jsonl file in the data folder."""

  benchmark_dataset = get_mbpp() if benchmark_name == "mbpp" else get_human_eval()
  queries = [example["prompt"] for example in benchmark_dataset.values()]
  logger.info(f"Benchmark {benchmark_name} Queries: {queries}")
  samples = await run_agent_batch(
      queries,
      entry_agent=entry_agent,
      session_id=session_id,
      user_id=user_id,
      runner=runner,
      app_name=app_name,
  )

  file_suffix = session_id if session_id else f"{str(int(time.time() * 1000))}"
  data_dir = Path("data")
  data_dir.mkdir(exist_ok=True)
  jsonl_path = (
      data_dir / samples / {benchmark_name} / f"{benchmark_name}_samples_{file_suffix}.jsonl"
  )
  with open(jsonl_path, "w") as f:
    for dataset_entry, sample in zip(benchmark_dataset.values(), samples):
      formatted_entry = {
          "task_id": str(dataset_entry["task_id"]),
          "solution": str(sample),
      }
      f.write(json.dumps(formatted_entry) + "\n")
  logger.info(f"Saved samples to {jsonl_path}")
  return jsonl_path
