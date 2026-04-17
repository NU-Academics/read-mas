#!/usr/bin/env bash
# Run the full LLM benchmarking pipeline (no agents):
#   1. Generate raw samples via direct LLM call
#   2. Sanitize with evalplus
#   3. Run DVC llm_code_benchmark experiment
#   4. Push to DVC remote
#   5. Commit dvc.lock
#
# Usage:
#   ./scripts/run-llm-benchmark.sh <model> <dataset> [samples_file]
#
# Arguments:
#   model        LLM model name (litellm format, e.g. anthropic/claude-sonnet-4-0)
#   dataset      humaneval | mbpp
#   samples_file (optional) existing .jsonl to resume generation from

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
  echo "Usage: $0 <model> <dataset> [samples_file]" >&2
  echo "" >&2
  echo "  model        litellm model string (e.g. anthropic/claude-sonnet-4-5)" >&2
  echo "  dataset      humaneval | mbpp" >&2
  echo "  samples_file (optional) path to existing .jsonl to resume from" >&2
  exit 1
}

MODEL="${1:-}"
DATASET="${2:-}"
SAMPLES="${3:-}"

if [ -z "$MODEL" ] || [ -z "$DATASET" ]; then
  echo "Error: model and dataset are required." >&2
  usage
fi

if [[ "$DATASET" != "humaneval" && "$DATASET" != "mbpp" ]]; then
  echo "Error: dataset must be 'humaneval' or 'mbpp', got '$DATASET'" >&2
  exit 1
fi

# Preserve branch and restore on exit (dvc exp run can detach HEAD)
ORIG_REF=$(git symbolic-ref --short HEAD 2>/dev/null || git rev-parse HEAD)
trap 'git checkout "$ORIG_REF" 2>/dev/null || true' EXIT

# --- Step 1: Generate samples ---
echo "=== Step 1: Generating LLM samples ==="
echo "  model=$MODEL  dataset=$DATASET"

GENERATE_CMD=(readmas-eval llm-generate-samples "$DATASET" -m "$MODEL")

if [ -n "$SAMPLES" ]; then
  echo "  Resuming from: $SAMPLES"
  GENERATE_CMD+=( -s "$SAMPLES")
fi

"${GENERATE_CMD[@]}"

# Use the provided samples file, or find the newest generated one
if [ -n "$SAMPLES" ]; then
  SAMPLES_FILE="$SAMPLES"
else
  SAMPLES_FILE=$(ls -t "data/samples/${DATASET}"/*.jsonl 2>/dev/null \
    | grep -v '\-sanitized' | head -n 1)
fi

if [ -z "$SAMPLES_FILE" ]; then
  echo "Error: no .jsonl sample file found in data/samples/${DATASET}/" >&2
  exit 1
fi

echo "  Generated samples: $SAMPLES_FILE"

# --- Step 2: Sanitize ---
echo ""
echo "=== Step 2: Sanitizing samples ==="
python -m evalplus.sanitize --samples "$SAMPLES_FILE"

SANITIZED_FILE="${SAMPLES_FILE%.jsonl}-sanitized.jsonl"

if [ ! -f "$SANITIZED_FILE" ]; then
  echo "Error: sanitized file not found: $SANITIZED_FILE" >&2
  exit 1
fi

echo "  Sanitized file: $SANITIZED_FILE"

# --- Step 3: DVC experiment ---
echo ""
echo "=== Step 3: Running DVC llm_code_benchmark experiment ==="
EXP_NAME="llm-${MODEL//[\/:]/-}-${DATASET}-$(date +%s)"
echo "  Experiment name: $EXP_NAME"

dvc exp run \
  -S "llm.model=${MODEL}" \
  -S "llm.dataset=${DATASET}" \
  -S "llm.samples=${SANITIZED_FILE}" \
  --name "$EXP_NAME" \
  --force \
  llm_code_benchmark

# --- Step 4: DVC push ---
echo ""
echo "=== Step 4: Pushing to DVC remote ==="
dvc push

# --- Step 5: Commit ---
echo ""
echo "=== Step 5: Committing dvc.lock and data/samples.dvc ==="
git add dvc.lock dvc.yaml params.yaml data/samples.dvc
git commit -m "LLM benchmark: ${MODEL} / ${DATASET}"

echo ""
echo "=== Done: $EXP_NAME ==="
