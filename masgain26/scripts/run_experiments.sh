#!/usr/bin/env bash
# Run DVC experiment pipeline for train, eval, or benchmark stages.
#
# Usage:
#   ./scripts/run_experiments.sh <stage> <agent> <model> <rag> [no_opt] [num_runs] [rag_index]
#
# Arguments:
#   stage      Stage to run: train | eval | benchmark
#   agent      Agent type: single_agent | read_agent
#   model      LLM model name (e.g. gemini-2.5-flash)
#   rag        Enable RAG: true | false
#   no_opt     Skip prompt optimization (train only): true | false  (default: false)
#   num_runs   Number of runs (eval/benchmark only, default: 1)
#   rag_index  RAG index to use (benchmark only): requirements | devbench_benchmark  (default: devbench_benchmark)
#
# Notes:
#   - train: single run only, no dvc push or git commit
#   - eval/benchmark: supports multiple runs; pushes and commits after each run

set -e

# Activate the project venv so the correct dvc/python are used, not system-installed ones.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_ACTIVATE="$SCRIPT_DIR/../.venv/bin/activate"
if [ -f "$VENV_ACTIVATE" ]; then
  # shellcheck source=/dev/null
  source "$VENV_ACTIVATE"
else
  echo "Warning: .venv not found at $SCRIPT_DIR/../.venv — using system Python/dvc" >&2
fi

usage() {
  echo "Usage: $0 <stage> <agent> <model> <rag> [no_opt] [num_runs] [rag_index]" >&2
  echo "" >&2
  echo "  stage      train | eval | benchmark" >&2
  echo "  agent      single_agent | read_agent | collector_agent | analyzer_agent | specifier_agent | designer_agent | documenter_agent" >&2
  echo "  model      LLM model name (e.g. gemini-2.5-flash)" >&2
  echo "  rag        true | false" >&2
  echo "  no_opt     true | false  (train only, default: false)" >&2
  echo "  num_runs   positive integer (eval/benchmark only, default: 1)" >&2
  echo "  rag_index  requirements | devbench_benchmark  (benchmark only, default: devbench_benchmark)" >&2
  exit 1
}

# --- Parse arguments ---
STAGE="${1:-}"
AGENT="${2:-}"
MODEL="${3:-}"
RAG="${4:-}"
NO_OPT="${5:-false}"
NUM_RUNS="${6:-1}"
RAG_INDEX="${7:-devbench_benchmark}"

# Sanitize model name for use in experiment names (replace '/' with '-')
MODEL_SAFE="${MODEL//[\/:]/-}"

# Required args
if [ -z "$STAGE" ] || [ -z "$AGENT" ] || [ -z "$MODEL" ] || [ -z "$RAG" ]; then
  echo "Error: stage, agent, model, and rag are required." >&2
  usage
fi

# Validate stage
if [[ "$STAGE" != "train" && "$STAGE" != "eval" && "$STAGE" != "benchmark" ]]; then
  echo "Error: stage must be 'train', 'eval', or 'benchmark', got '$STAGE'" >&2
  exit 1
fi

# Validate agent
if [[ "$AGENT" != "single_agent" && "$AGENT" != "read_agent" && "$AGENT" != "collector_agent" && "$AGENT" != "analyzer_agent" && "$AGENT" != "specifier_agent" && "$AGENT" != "designer_agent" && "$AGENT" != "documenter_agent" ]]; then
  echo "Error: agent must be one of the readmas agents, got '$AGENT'" >&2
  exit 1
fi

# Validate rag
if [[ "$RAG" != "true" && "$RAG" != "false" ]]; then
  echo "Error: rag must be 'true' or 'false', got '$RAG'" >&2
  exit 1
fi

# Validate no_opt (only meaningful for train, but validate if provided)
if [[ "$NO_OPT" != "true" && "$NO_OPT" != "false" ]]; then
  echo "Error: no_opt must be 'true' or 'false', got '$NO_OPT'" >&2
  exit 1
fi

# Validate num_runs (only for eval/benchmark)
if [[ "$STAGE" != "train" ]]; then
  if ! [[ "$NUM_RUNS" =~ ^[0-9]+$ ]] || [ "$NUM_RUNS" -lt 1 ]; then
    echo "Error: num_runs must be a positive integer, got '$NUM_RUNS'" >&2
    exit 1
  fi
fi

# Preserve branch and restore on exit (dvc exp run can detach HEAD)
ORIG_REF=$(git symbolic-ref --short HEAD 2>/dev/null || git rev-parse HEAD)
trap 'git checkout "$ORIG_REF" 2>/dev/null || true' EXIT

# --- Run train (single run, no push/commit) ---
if [ "$STAGE" = "train" ]; then
  echo "=== Running train stage ==="
  echo "  agent=$AGENT  model=$MODEL  rag=$RAG  no_opt=$NO_OPT"
  EXP_NAME="train-${AGENT}-${MODEL_SAFE}-$(date +%s)"

  dvc exp run \
    -S "train.agent_name=${AGENT}" \
    -S "train.model=${MODEL}" \
    -S "train.rag=${RAG}" \
    -S "train.no_opt=${NO_OPT}" \
    --name "$EXP_NAME" \
    --force \
    train

  echo "=== Train complete: $EXP_NAME ==="
  exit 0
fi

# --- Run eval or benchmark (multi-run, push + commit) ---
echo "=== Running $STAGE stage ($NUM_RUNS run(s)) ==="
if [ "$STAGE" = "benchmark" ]; then
  echo "  agent=$AGENT  model=$MODEL  rag=$RAG  rag_index=$RAG_INDEX"
else
  echo "  agent=$AGENT  model=$MODEL  rag=$RAG"
fi

for i in $(seq 1 "$NUM_RUNS"); do
  echo ""
  echo "--- Run $i of $NUM_RUNS ---"
  EXP_NAME="${STAGE}-${AGENT}-${MODEL_SAFE}-$(date +%s)"

  if [ "$STAGE" = "benchmark" ]; then
    dvc exp run \
      -S "benchmark.agent_name=${AGENT}" \
      -S "benchmark.model=${MODEL}" \
      -S "benchmark.rag=${RAG}" \
      -S "benchmark.rag_index=${RAG_INDEX}" \
      --name "$EXP_NAME" \
      --force \
      benchmark
  else
    dvc exp run \
      -S "${STAGE}.agent_name=${AGENT}" \
      -S "${STAGE}.model=${MODEL}" \
      -S "${STAGE}.rag=${RAG}" \
      --name "$EXP_NAME" \
      --force \
      "$STAGE"
  fi

  dvc push
  git add dvc.lock dvc.yaml params.yaml data/goldens.dvc data/samples.dvc eval_data/files
  if [ "$STAGE" = "benchmark" ]; then
    git commit -m "${STAGE} exp: ${AGENT} / ${MODEL} (rag=${RAG}, index=${RAG_INDEX}) run $i of $NUM_RUNS"
  else
    git commit -m "${STAGE} exp: ${AGENT} / ${MODEL} (rag=${RAG}) run $i of $NUM_RUNS"
  fi

  echo "--- Completed run $i of $NUM_RUNS: $EXP_NAME ---"
done

echo ""
echo "=== All $NUM_RUNS $STAGE run(s) finished ==="
