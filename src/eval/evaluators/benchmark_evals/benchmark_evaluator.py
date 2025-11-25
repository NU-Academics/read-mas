from evalplus.data.humaneval import get_human_eval
from evalplus.data.mbpp import get_mbpp_plus
from typing import Optional
from google.adk.agents import Agent
from google.adk.runners import Runner
from orchestrator.orchestrator import run_agent
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
    samples_file_path: Optional[str] = None,
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

    Returns:
      Path to the samples jsonl file
    """

    # Use get_mbpp_plus() for MBPP to match what evalplus.evaluate() expects
    benchmark_dataset = (
        get_mbpp_plus() if benchmark_name == "mbpp" else get_human_eval()
    )
    # Create list of (task_id, entry) tuples to preserve task_id mapping
    dataset_entries = [(task_id, entry) for task_id, entry in benchmark_dataset.items()]
    queries = [entry["prompt"] for _, entry in dataset_entries]

    # Determine output file path
    if samples_file_path:
        jsonl_path = Path(samples_file_path)
        if not jsonl_path.exists():
            logger.warning(
                f"Samples file {jsonl_path} does not exist. Creating new file."
            )
            jsonl_path.parent.mkdir(parents=True, exist_ok=True)
            existing_task_ids = set()
        else:
            # Read existing task_ids from the file
            existing_task_ids = set()
            try:
                with open(jsonl_path, "r") as f:
                    for line in f:
                        if line.strip():
                            entry = json.loads(line)
                            existing_task_ids.add(str(entry["task_id"]))
                logger.info(
                    f"Found {len(existing_task_ids)} existing samples in {jsonl_path}"
                )
            except Exception as e:
                logger.error(
                    f"Error reading existing samples file: {e}. Starting fresh."
                )
                existing_task_ids = set()
    else:
        file_suffix = session_id if session_id else f"{str(int(time.time() * 1000))}"
        data_dir = Path("data")
        data_dir.mkdir(exist_ok=True)
        samples_dir = data_dir / "samples" / benchmark_name
        samples_dir.mkdir(parents=True, exist_ok=True)
        jsonl_path = samples_dir / f"{benchmark_name}_samples_{file_suffix}.jsonl"
        existing_task_ids = set()

    # Filter out queries that already have samples
    remaining_entries = []
    remaining_queries = []
    for (task_id, entry), query in zip(dataset_entries, queries):
        task_id_str = str(task_id)
        if task_id_str not in existing_task_ids:
            remaining_entries.append((task_id, entry))
            remaining_queries.append(query)

    if not remaining_queries:
        logger.info(f"All samples already exist in {jsonl_path}. No generation needed.")
        return jsonl_path

    logger.info(
        f"Generating {len(remaining_queries)} samples for benchmark {benchmark_name} (out of {len(queries)} total)"
    )

    # Process queries one by one and write after each completion
    # Use append mode if file exists (resuming), otherwise write mode (new file)
    mode = "a" if jsonl_path.exists() else "w"
    with open(jsonl_path, mode) as f:
        for i, ((task_id, dataset_entry), query) in enumerate(
            zip(remaining_entries, remaining_queries), 1
        ):
            try:
                logger.info(
                    f"Processing sample {i}/{len(remaining_queries)}: {task_id}"
                )
                sample = await run_agent(
                    query,
                    entry_agent=entry_agent,
                    app_name=app_name,
                )

                formatted_entry = {
                    "task_id": str(task_id),
                    "solution": str(sample),
                }
                f.write(json.dumps(formatted_entry) + "\n")
                f.flush()  # Ensure data is written immediately
                logger.info(f"Saved sample for {task_id} to {jsonl_path}")
            except Exception as e:
                logger.error(f"Error generating sample for {task_id}: {e}")
                # Continue with next sample even if one fails
                continue

    logger.info(f"Completed generation. Samples saved to {jsonl_path}")
    return jsonl_path
