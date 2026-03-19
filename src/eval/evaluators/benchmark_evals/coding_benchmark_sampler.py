import asyncio
import json
import time
from pathlib import Path
from typing import Optional

from evalplus.data.humaneval import get_human_eval
from evalplus.data.mbpp import get_mbpp_plus
from google.adk.agents import Agent
from google.adk.runners import Runner
from loguru import logger

from orchestrator.constants import APP_NAME
from orchestrator.orchestrator import (
    create_app_context,
    run_agent,
    run_agent_with_context,
)
from utils.constants import (AgentRunMode, NUMBER_OF_TRIES)


async def generate_benchmark_samples(
    entry_agent: Agent,
    benchmark_name: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    runner: Optional[Runner] = None,
    app_name: Optional[str] = APP_NAME,
    samples_file_path: Optional[str] = None,
    num_samples: int = NUMBER_OF_TRIES,
    concurrency: int = 5,
):
  """Generate samples for a benchmark using the evaluation coding agent. The samples are saved to a jsonl file in the data folder.

  Args:
    entry_agent: The agent to use for generating samples
    benchmark_name: Name of the benchmark (e.g., "humaneval", "mbpp")
    session_id: Optional session ID for the agent run
    user_id: Optional user ID for the agent run
    runner: Optional runner for the agent run
    app_name: Optional app name for the agent run
    samples_file_path: Optional path to an existing samples file. If provided, will resume
      generation from where it stopped, writing missing samples to complete the file.
    num_samples: Total number of samples to generate per benchmark task
  Returns:
    Path to the samples jsonl file
  """

  benchmark_dataset = get_mbpp_plus() if benchmark_name == "mbpp" else get_human_eval()
  dataset_entries = [(task_id, entry) for task_id, entry in benchmark_dataset.items()]
  queries = [entry["prompt"] for _, entry in dataset_entries]

  # Determine output file path
  existing_samples_count = {}  # Dict mapping task_id -> count
  if samples_file_path:
    jsonl_path = Path(samples_file_path)
    if not jsonl_path.exists():
      logger.warning(f"Samples file {jsonl_path} does not exist. Creating new file.")
      jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    else:
      # Read existing samples and count per task
      try:
        with open(jsonl_path, "r") as f:
          for line in f:
            if line.strip():
              entry = json.loads(line)
              task_id_str = str(entry["task_id"])
              existing_samples_count[task_id_str] = existing_samples_count.get(task_id_str, 0) + 1
        total_existing = sum(existing_samples_count.values())
        logger.info(
            f"Found {total_existing} existing samples across {len(existing_samples_count)} tasks in"
            f" {jsonl_path}"
        )
      except Exception as e:
        logger.error(f"Error reading existing samples file: {e}. Starting fresh.")
        existing_samples_count = {}
  else:
    file_suffix = session_id if session_id else f"{str(int(time.time() * 1000))}"
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    samples_dir = data_dir / "samples" / benchmark_name
    samples_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = samples_dir / f"{benchmark_name}_samples_{file_suffix}.jsonl"

    # Filter tasks that need more samples
  remaining_entries = []
  remaining_queries = []
  remaining_sample_counts = []  # Track how many samples each task still needs
  for (task_id, entry), query in zip(dataset_entries, queries):
    task_id_str = str(task_id)
    existing_count = existing_samples_count.get(task_id_str, 0)
    needed = num_samples - existing_count
    if needed > 0:
      remaining_entries.append((task_id, entry))
      remaining_queries.append(query)
      remaining_sample_counts.append(needed)

  if not remaining_queries:
    logger.info(f"All samples already exist in {jsonl_path}. No generation needed.")
    return jsonl_path

  total_samples_needed = sum(remaining_sample_counts)
  logger.info(
      f"Generating {total_samples_needed} samples for {len(remaining_queries)} tasks in benchmark"
      f" {benchmark_name} (out of {len(queries)} total tasks, {num_samples} samples per task)"
  )

  # Build reusable App/Runner context once
  _app, ctx_runner, ctx_session_manager = await create_app_context(
      entry_agent, app_name=app_name, run_mode=AgentRunMode.CODE_BENCHMARK
  )

  # Flatten task×sample into a list of work items
  work_items = []
  for task_idx, ((task_id, _dataset_entry), query, num_needed) in enumerate(
      zip(remaining_entries, remaining_queries, remaining_sample_counts), 1
  ):
    for sample_idx in range(num_needed):
      work_items.append((task_id, query, task_idx, sample_idx, num_needed))

  semaphore = asyncio.Semaphore(concurrency)
  write_lock = asyncio.Lock()
  completed = 0

  mode = "a" if jsonl_path.exists() else "w"
  with open(jsonl_path, mode) as f:

    async def _process_sample(item_num, task_id, query, task_idx, sample_idx, num_needed):
      nonlocal completed
      async with semaphore:
        try:
          logger.info(
              f"Processing sample {item_num}/{total_samples_needed} (task"
              f" {task_idx}/{len(remaining_entries)}: {task_id}, sample"
              f" {sample_idx + 1}/{num_needed})"
          )
          sample = await run_agent_with_context(
              query, ctx_runner, ctx_session_manager, app_name=app_name
          )

          formatted_entry = {
              "task_id": str(task_id),
              "solution": str(sample),
          }
          async with write_lock:
            f.write(json.dumps(formatted_entry) + "\n")
            f.flush()

          completed += 1
          logger.info(
              f"Saved sample {sample_idx + 1}/{num_needed} for {task_id}"
              f" ({completed}/{total_samples_needed} done)"
          )
        except Exception as e:
          logger.error(f"Error generating sample {sample_idx + 1}/{num_needed} for {task_id}: {e}")

    async with asyncio.TaskGroup() as tg:
      for item_num, (task_id, query, task_idx, sample_idx, num_needed) in enumerate(work_items, 1):
        tg.create_task(_process_sample(item_num, task_id, query, task_idx, sample_idx, num_needed))

  logger.info(f"Completed generation. Samples saved to {jsonl_path}")
  return jsonl_path
