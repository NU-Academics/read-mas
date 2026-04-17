#!/usr/bin/env bash
# Run the full code benchmarking pipeline:
#   1. Generate samples via readmas-eval
#   2. Sanitize with evalplus
#   3. Run DVC code_benchmark experiment
#   4. Push to DVC remote
#   5. Commit dvc.lock and eval_data/files
#
# Usage:
#   ./scripts/run-code-benchmark.sh <agent> <model> <rag> <dataset> [samples_file]
#
# Arguments:
#   agent        Agent type: single_agent | read_agent
#   model        LLM model name, e.g. gemini-2.5-flash
#   rag          Enable RAG: true | false
#   dataset      Benchmark dataset: humaneval | mbpp
#   samples_file (optional) Path to an existing .jsonl samples file to resume from

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
  echo "Usage: $0 <agent> <model> <rag> <dataset> [samples_file]" >&2
  echo "" >&2
  echo "  agent        single_agent | read_agent" >&2
  echo "  model        LLM model name (e.g. gemini-2.5-flash)" >&2
  echo "  rag          true | false" >&2
  echo "  dataset      humaneval | mbpp" >&2
  echo "  samples_file (optional) path to existing .jsonl to resume from" >&2
  exit 1
}

# --- Parse arguments ---
AGENT="${1:-}"
MODEL="${2:-}"
RAG="${3:-}"
DATASET="${4:-}"
SAMPLES="${5:-}"

if [ -z "$AGENT" ] || [ -z "$MODEL" ] || [ -z "$RAG" ] || [ -z "$DATASET" ]; then
  echo "Error: agent, model, rag, and dataset are required." >&2
  usage
fi

if [[ "$AGENT" != "single_agent" && "$AGENT" != "read_agent" ]]; then
  echo "Error: agent must be 'single_agent' or 'read_agent', got '$AGENT'" >&2
  exit 1
fi

if [[ "$DATASET" != "humaneval" && "$DATASET" != "mbpp" ]]; then
  echo "Error: dataset must be 'humaneval' or 'mbpp', got '$DATASET'" >&2
  exit 1
fi

if [[ "$RAG" != "true" && "$RAG" != "false" ]]; then
  echo "Error: rag must be 'true' or 'false', got '$RAG'" >&2
  exit 1
fi

# Preserve branch and restore on exit (dvc exp run can detach HEAD)
ORIG_REF=$(git symbolic-ref --short HEAD 2>/dev/null || git rev-parse HEAD)
trap 'git checkout "$ORIG_REF" 2>/dev/null || true' EXIT

# --- Step 1: Generate samples ---
echo "=== Step 1: Generating samples ==="
echo "  agent=$AGENT  model=$MODEL  rag=$RAG  dataset=$DATASET"

GENERATE_CMD=(readmas-eval generate-samples "$DATASET" -t "$AGENT" -m "$MODEL")

if [ "$RAG" = "true" ]; then
  GENERATE_CMD+=( -r true)
fi

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
echo "=== Step 3: Running DVC code_benchmark experiment ==="
EXP_NAME="code-${AGENT}-${MODEL//[\/:]/-}-${DATASET}-$(date +%s)"
echo "  Experiment name: $EXP_NAME"

dvc exp run \
  -S "code.agent_name=${AGENT}" \
  -S "code.model=${MODEL}" \
  -S "code.dataset=${DATASET}" \
  -S "code.rag=${RAG}" \
  -S "code.samples=${SANITIZED_FILE}" \
  --name "$EXP_NAME" \
  --force \
  code_benchmark

# --- Step 4: DVC push ---
echo ""
echo "=== Step 4: Pushing to DVC remote ==="
dvc push

# --- Step 5: Commit ---
echo ""
echo "=== Step 5: Committing dvc.lock and eval_data/files ==="
git add dvc.lock dvc.yaml params.yaml data/goldens.dvc data/samples.dvc eval_data/files
git commit -m "Code benchmark: ${AGENT} / ${MODEL} / ${DATASET} (rag=${RAG})"

echo ""
echo "=== Done: $EXP_NAME ==="
