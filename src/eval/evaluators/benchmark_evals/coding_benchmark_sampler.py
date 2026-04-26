import asyncio
import json
import time
from pathlib import Path
from typing import Awaitable, Callable, Optional

from evalplus.data.humaneval import get_human_eval
from evalplus.data.mbpp import get_mbpp_plus
from google.adk.agents import Agent
from google.adk.runners import Runner
from litellm import acompletion
from loguru import logger

from orchestrator.constants import APP_NAME
from orchestrator.orchestrator import (
    create_app_context,
    run_agent_with_context,
)
from utils.constants import (AgentRunMode, NUMBER_OF_TRIES, LOCAL_LLM_TASK_TIMEOUT)

LLM_SAMPLER_SYSTEM_PROMPT = """You are an expert Python programmer. Complete the given Python function.

## CRITICAL REQUIREMENTS:
- **FORBIDDEN**: DO NOT write unit tests - only generate the function implementation code
- **FORBIDDEN**: Do NOT call helper functions or utilities that are not defined in the same
  code block. Every function you call must be defined inline in your response.
- **FORBIDDEN**: Do NOT add isinstance() checks, type guards, or raise exceptions for edge
  cases. Trust the caller's inputs and implement the simplest, most direct logic possible.
- Return only the code without explanations or markdown formatting unless the code itself requires markdown.
- **CRITICAL**: LIMIT doc strings and code comments to at most 2 sentences.
- Apply proper indenting to the Python function body you are generating
- **CRITICAL**: Return ONLY the code continuation — no markdown fences, no explanations, no tests
"""


async def _generate_samples_with_fn(
    benchmark_name: str,
    sample_fn: Callable[[str, dict], Awaitable[str]],
    samples_file_path: Optional[str] = None,
    num_samples: int = NUMBER_OF_TRIES,
    concurrency: int = 16,
) -> Path:
  """Shared scaffold for generating benchmark samples.

  Args:
    benchmark_name: Name of the benchmark (e.g., "humaneval", "mbpp")
    sample_fn: Async callable (task_id, entry) -> solution string
    samples_file_path: Optional path to existing samples file for resuming
    num_samples: Total number of samples to generate per benchmark task
    concurrency: Maximum number of concurrent calls

  Returns:
    Path to the samples jsonl file
  """
  benchmark_dataset = get_mbpp_plus() if benchmark_name == "mbpp" else get_human_eval()
  dataset_entries = [(task_id, entry) for task_id, entry in benchmark_dataset.items()]

  existing_samples_count = {}
  if samples_file_path:
    jsonl_path = Path(samples_file_path)
    if not jsonl_path.exists():
      logger.warning(f"Samples file {jsonl_path} does not exist. Creating new file.")
      jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    else:
      try:
        with open(jsonl_path, "r") as f:
          for line in f:
            if line.strip():
              entry = json.loads(line)
              task_id_str = str(entry["task_id"])
              existing_samples_count[task_id_str] = existing_samples_count.get(task_id_str, 0) + 1
        total_existing = sum(existing_samples_count.values())
        logger.info(
            f"Found {total_existing} existing samples across {len(existing_samples_count)} tasks"
            f" in {jsonl_path}"
        )
      except Exception as e:
        logger.error(f"Error reading existing samples file: {e}. Starting fresh.")
        existing_samples_count = {}
  else:
    file_suffix = str(int(time.time() * 1000))
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    samples_dir = data_dir / "samples" / benchmark_name
    samples_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = samples_dir / f"{benchmark_name}_samples_{file_suffix}.jsonl"

  remaining_entries = []
  remaining_sample_counts = []
  for task_id, entry in dataset_entries:
    task_id_str = str(task_id)
    existing_count = existing_samples_count.get(task_id_str, 0)
    needed = num_samples - existing_count
    if needed > 0:
      remaining_entries.append((task_id, entry))
      remaining_sample_counts.append(needed)

  if not remaining_entries:
    logger.info(f"All samples already exist in {jsonl_path}. No generation needed.")
    return jsonl_path

  total_samples_needed = sum(remaining_sample_counts)
  logger.info(
      f"Generating {total_samples_needed} samples for {len(remaining_entries)} tasks in benchmark"
      f" {benchmark_name} (out of {len(dataset_entries)} total tasks, {num_samples} samples"
      " per task)"
  )

  work_items = []
  for task_idx, ((task_id, entry), num_needed) in enumerate(
      zip(remaining_entries, remaining_sample_counts), 1
  ):
    for sample_idx in range(num_needed):
      work_items.append((task_id, entry, task_idx, sample_idx, num_needed))

  semaphore = asyncio.Semaphore(concurrency)
  write_lock = asyncio.Lock()
  completed = 0

  mode = "a" if jsonl_path.exists() else "w"
  with open(jsonl_path, mode) as f:

    async def _process_sample(item_num, task_id, entry, task_idx, sample_idx, num_needed):
      nonlocal completed
      async with semaphore:
        try:
          logger.info(
              f"Processing sample {item_num}/{total_samples_needed} (task"
              f" {task_idx}/{len(remaining_entries)}: {task_id}, sample"
              f" {sample_idx + 1}/{num_needed})"
          )
          solution = await asyncio.wait_for(
              sample_fn(task_id, entry), timeout=LOCAL_LLM_TASK_TIMEOUT
          )

          formatted_entry = {"task_id": str(task_id), "solution": str(solution)}
          async with write_lock:
            f.write(json.dumps(formatted_entry) + "\n")
            f.flush()

          completed += 1
          logger.info(
              f"Saved sample {sample_idx + 1}/{num_needed} for {task_id}"
              f" ({completed}/{total_samples_needed} done)"
          )
        except asyncio.TimeoutError:  # ← new
          logger.warning(  # ← new
              f"Task timeout ({LOCAL_LLM_TASK_TIMEOUT}s) for {task_id}"
              f" sample {sample_idx + 1}/{num_needed}. Skipping."
          )
        except Exception as e:
          logger.error(f"Error generating sample {sample_idx + 1}/{num_needed} for {task_id}: {e}")

    async with asyncio.TaskGroup() as tg:
      for item_num, (task_id, entry, task_idx, sample_idx, num_needed) in enumerate(work_items, 1):
        tg.create_task(_process_sample(item_num, task_id, entry, task_idx, sample_idx, num_needed))

  logger.info(f"Completed generation. Samples saved to {jsonl_path}")
  return jsonl_path


async def generate_benchmark_samples(
    entry_agent: Agent,
    benchmark_name: str,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    runner: Optional[Runner] = None,
    app_name: Optional[str] = APP_NAME,
    samples_file_path: Optional[str] = None,
    num_samples: int = NUMBER_OF_TRIES,
    concurrency: int = 8,
):
  """Generate samples for a benchmark using the evaluation coding agent.

  Args:
    entry_agent: The agent to use for generating samples
    benchmark_name: Name of the benchmark (e.g., "humaneval", "mbpp")
    session_id: Optional session ID for the agent run
    user_id: Optional user ID for the agent run
    runner: Optional runner for the agent run
    app_name: Optional app name for the agent run
    samples_file_path: Optional path to an existing samples file for resuming
    num_samples: Total number of samples to generate per benchmark task
    concurrency: Maximum number of concurrent agent calls

  Returns:
    Path to the samples jsonl file
  """
  _app, ctx_runner, ctx_session_manager = await create_app_context(
      entry_agent, app_name=app_name, run_mode=AgentRunMode.CODE_BENCHMARK
  )

  async def sample_fn(task_id, entry):
    return await run_agent_with_context(
        entry["prompt"], ctx_runner, ctx_session_manager, app_name=app_name
    )

  return await _generate_samples_with_fn(
      benchmark_name, sample_fn, samples_file_path, num_samples, concurrency
  )


async def generate_llm_samples(
    model: str,
    benchmark_name: str,
    samples_file_path: Optional[str] = None,
    num_samples: int = NUMBER_OF_TRIES,
    concurrency: int = 8,
) -> Path:
  """Generate benchmark samples by calling an LLM directly (no agent orchestration).

  Args:
    model: LiteLLM-format model string (e.g., "anthropic/claude-sonnet-4-0")
    benchmark_name: Name of the benchmark (e.g., "humaneval", "mbpp")
    samples_file_path: Optional path to an existing samples file for resuming
    num_samples: Total number of samples to generate per benchmark task
    concurrency: Maximum number of concurrent LLM calls

  Returns:
    Path to the samples jsonl file
  """

  async def sample_fn(task_id, entry):
    resp = await acompletion(
        model=model,
        messages=[
            {"role": "system", "content": LLM_SAMPLER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Complete this Python function:\n\n{entry['prompt']}",
            },
        ],
    )
    body = resp.choices[0].message.content
    return entry["prompt"] + body

  return await _generate_samples_with_fn(
      benchmark_name, sample_fn, samples_file_path, num_samples, concurrency
  )


async def generate_benchmark_samples_local_llm(
    evaluated_agent: Agent,
    benchmark_name: str,
    app_name: str = APP_NAME,
    samples_file_path: Optional[str] = None,
    num_samples: int = NUMBER_OF_TRIES,
    concurrency: int = 4,
) -> Path:
  """Generate samples using a deterministic two-step pipeline: design agent → generate_code.

  For local/small models that don't reliably follow multi-step tool-calling instructions.
  Step 1: run the design agent to get SRS/design output.
  Step 2: call generate_code directly with that output.
  """
  from eval.eval_tools import generate_code

  _app, ctx_runner, ctx_session_manager = await create_app_context(
      evaluated_agent, app_name=app_name, run_mode=AgentRunMode.CODE_BENCHMARK
  )

  async def sample_fn(task_id, entry):
    design = await run_agent_with_context(
        entry["prompt"], ctx_runner, ctx_session_manager, app_name=app_name
    )
    return await generate_code(design_output=design, original_prompt=entry["prompt"])

  return await _generate_samples_with_fn(
      benchmark_name, sample_fn, samples_file_path, num_samples, concurrency
  )
