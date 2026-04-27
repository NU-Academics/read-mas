#!/usr/bin/env bash
# Export DVC experiment results to CSV for a given stage and commit range.
#
# Usage:
#   ./scripts/export_experiments.sh <agent> <stage> <model> <start_commit> <end_commit> <dataset>
#
# Arguments:
#   agent         The agent under training, eval or benchmarking
#   stage         Stage to export: train | eval | benchmark | code_benchmark
#   model         The model used to run the experiment: claude | gemini | ollama | openai
#   start_commit  Git commit hash or tag marking the earliest experiment to include
#   end_commit    Git commit hash for the cutoff experiment
#   dataset       The dataset (for code benchmarks): humaneval | mbpp 
# Output:
#   benchmark_runs/<agent>_<stage>[_dataset]_<model>.csv

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
  echo "Usage: $0 <agent> <stage> <model> <start_commit> <end_commit> <dataset>" >&2
  echo "" >&2
  echo "  agent         single_agent | collector_agent..." >&2
  echo "  stage         train | eval | benchmark | code_benchmark" >&2
  echo "  model         claude | gemini | ollama | openai" >&2
  echo "  start_commit  git commit hash or tag (e.g. 02ca4a8, v1.0)" >&2
  echo "  end_commit    git commit hash or tag (e.g. 02ca4a8, v1.0)" >&2
  echo "  dataset       humaneval | mbpp" >&2
  exit 1
}

# --- Parse arguments ---
AGENT="${1:-}"
STAGE="${2:-}"
MODEL="${3:-}"
START_COMMIT="${4:-}"
END_COMMIT="${5:-}"
DATASET="${6:-}"

if [ -z "$AGENT" ] || [ -z "$STAGE" ] || [ -z "$MODEL" ] || [ -z "$START_COMMIT" ] || [ -z "$END_COMMIT" ]; then
  echo "Error: agent, stage, model, start_commit, and end_commit are required." >&2
  usage
fi

# Validate agent
case "$AGENT" in
  single_agent|collector_agent|analyzer_agent|specifier_agent|designer_agent|documenter_agent|re_agent|design_agent|read_agent|llm)
    ;;
  *)
    echo "Error: agent must be a valid READ-MAS agent name." >&2
    exit 1
    ;;
esac

# Validate stage
case "$STAGE" in
  train|eval|benchmark|code_benchmark|llm_code_benchmark)
    ;;
  *)
    echo "Error: stage must be one of: train, eval, benchmark, code_benchmark" >&2
    exit 1
    ;;
esac

# Validate model
case "$MODEL" in
  claude|gemini|ollama|openai)
    ;;
  *)
    echo "Error: model must be one of: claude, gemini, ollama, openai" >&2
    exit 1
    ;;
esac

# Validate that start_commit exists
if ! git rev-parse --verify "$START_COMMIT" > /dev/null 2>&1; then
  echo "Error: '$START_COMMIT' is not a valid git commit or tag." >&2
  exit 1
fi

# Validate that end_commit exists
if ! git rev-parse --verify "$END_COMMIT" > /dev/null 2>&1; then
  echo "Error: '$END_COMMIT' is not a valid git commit or tag." >&2
  exit 1
fi

# Preserve branch and restore on exit (dvc exp show --rev can detach HEAD)
ORIG_REF=$(git symbolic-ref --short HEAD 2>/dev/null || git rev-parse HEAD)
trap 'git checkout "$ORIG_REF" 2>/dev/null || true' EXIT

# --- Stage-specific drop patterns ---
# Each pattern drops all other stages' params/outputs, keeping the current stage's columns.
case "$STAGE" in
  train)
    DROP='eval.*|benchmark.*|code.*|data*|src*|runs/eval*|runs/benchmark*|runs/code*|runs/llm*|prompts*'
    ;;
  eval)
    DROP='train.*|benchmark.*|code.*|data*|src*|runs/train*|runs/benchmark*|runs/code*|runs/llm*|prompts*'
    ;;
  benchmark)
    DROP='train.*|eval.*|code.*|data*|src*|runs/train*|runs/eval*|runs/code*|runs/llm*|prompts*'
    ;;
  code_benchmark)
    DROP='train.*|eval.*|benchmark.*|data*|src*|runs/train*|runs/eval*|runs/benchmark*|runs/llm*|prompts*'
    ;;
  llm_code_benchmark)
    DROP='train.*|eval.*|benchmark.*|data*|src*|runs/train*|runs/eval*|runs/benchmark*|runs/code*|code*|prompts*'
    ;;
esac

# --- Compute commit range ---
# Count commits after start_commit up to HEAD, then add 1 to include start_commit itself.
COMMITS_AFTER=$(git rev-list --count "${START_COMMIT}..${END_COMMIT}")
NUM_COMMITS=$((COMMITS_AFTER + 1))

OUTPUT_FILE="benchmark_runs/${AGENT}_${STAGE}"

if [ -n "$DATASET" ]; then
  OUTPUT_FILE+=_"$DATASET"
fi

OUTPUT_FILE+=_"$MODEL".csv

echo "=== Exporting DVC experiments ==="
echo "  agent:        $AGENT"
echo "  stage:        $STAGE"
echo "  model:        $MODEL"
echo "  start_commit: $START_COMMIT"
echo "  end_commit:   $END_COMMIT"
echo "  commits:      last $NUM_COMMITS (from $START_COMMIT to $END_COMMIT)"
echo "  dataset:      $DATASET"
echo "  output:       $OUTPUT_FILE"
echo ""

# --- Run dvc exp show ---
dvc exp show \
  --csv \
  --hide-workspace \
  --rev "$END_COMMIT" \
  -n "$NUM_COMMITS" \
  --drop "$DROP" \
  > "$OUTPUT_FILE"

echo "=== Done: exported to $OUTPUT_FILE ==="
