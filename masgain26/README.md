# masgain26 — RQ1 & RQ2 Reproduction Package

This folder is a scoped copy of the READ-MAS (Requirements and Design Multi-Agent System)
repository, containing only the code and data needed to reproduce the results reported for:

- **RQ1** — Does using multiple agents (the `read_agent` multi-agent pipeline) compared to a
  single agent (`single_agent`) improve generated-code quality (HumanEval / MBPP pass@1,
  pass@1+) and generated-design quality (custom LLM-as-a-Judge design accuracy, RAGAS
  faithfulness)?
- **RQ2** — Does Retrieval-Augmented Generation (RAG) improve `read_agent` design accuracy,
  compared to the same agent without RAG, using (a) a general requirements corpus and (b) a
  DevBench-specific corpus as the retrieval index?

RQ1 and RQ2 above are how these two questions are framed in the masgain26 paper; in the parent
dissertation they correspond to RQ1 and RQ5 respectively (the dissertation's own RQ2 is a
cross-LLM comparison, and RQ4 compares READ-MAS to a plain LLM — both are unrelated questions
excluded from this package, not renamed here).

No files were moved out of the original repository — everything here is a copy. This package
intentionally excludes code/data tied to the dissertation's RQ2 (cross-LLM comparison), RQ3, and
RQ4 (READ-MAS vs. plain LLM), which are out of scope for the accompanying paper.

## Contents

```
src/                    Agent implementations, orchestrator, RAG pipeline, eval framework
scripts/                Shell wrappers around the DVC pipeline (RQ1/RQ2-relevant only)
data/goldens/           Benchmark task definitions (read_agent, single_agent) used by RQ1
data/samples/           HumanEval/MBPP code samples referenced by the RQ1 benchmark_runs CSVs
datasets/               Requirements corpora (PROMISE, PURE) + DevBench used to build the RAG
                         indexes exercised in RQ2, and the prebuilt FAISS indexes themselves
benchmark_runs/         DVC experiment tables (CSV) backing the RQ1/RQ2 statistics
notebooks/data_analysis/data_analysis_rq1_rq2.ipynb
                        Trimmed analysis notebook: ANOVA/Kruskal-Wallis + post-hoc tests for
                        RQ1 and RQ2 only
dvc.yaml, params.yaml   DVC pipeline definitions, restricted to the `benchmark` and
                        `code_benchmark` stages used by RQ1/RQ2
pyproject.toml, uv.lock Full dependency lockfile from the parent project
.env.example            Required environment variables (no secrets)
```

## Setup

```bash
uv venv --python 3.12
uv sync --frozen        # installs exactly what's pinned in uv.lock — do not use
                         # `uv pip install -e .` here, it re-resolves deps from
                         # scratch and can drift onto incompatible versions
cp .env.example .env    # fill in GOOGLE_API_KEY / OPENAI_API_KEY
```

`--python 3.12` matters: `uv.lock` was resolved against Python 3.12, and this project pins
several fast-moving dependencies (e.g. `google-adk`) loosely in `pyproject.toml`. Installing on
a different interpreter without `--frozen` can silently pull newer, incompatible versions (a
newer `google-adk`, for example, moved `McpToolset` and breaks agent imports).

The Gemini and GPT-5-mini experiments require live API keys (`GOOGLE_API_KEY`,
`OPENAI_API_KEY`). Design-accuracy and RAGAS scoring use `deepeval`/`ragas`, which also call
out to an LLM judge — the same keys cover this.

## Reanalyzing the already-collected results (no API calls needed)

The `benchmark_runs/*.csv` files are the actual DVC experiment tables produced by the original
runs. To regenerate every statistical test and plot reported for RQ1 and RQ2 from this
already-collected data, first register a Jupyter kernel for this venv (only needed once —
`jupyter` on your `PATH` may point to an unrelated environment that can't see these packages):

```bash
.venv/bin/python -m ipykernel install --user --name masgain26 --display-name "Python (masgain26)"
```

Then either execute it headlessly:

```bash
.venv/bin/jupyter nbconvert --to notebook --execute \
  notebooks/data_analysis/data_analysis_rq1_rq2.ipynb \
  --output data_analysis_rq1_rq2.executed.ipynb
```

or launch `.venv/bin/jupyter lab` and open
`notebooks/data_analysis/data_analysis_rq1_rq2.ipynb` — it already defaults to the
"Python (masgain26)" kernel — and run all cells.

## Reproducing the experiments end-to-end

### RQ1 — single vs. multi-agent

For each model (`gemini-2.5-flash`, or an OpenAI GPT-5-mini equivalent) and each agent
(`single_agent`, `read_agent`), run the custom design benchmark and both code benchmarks:

```bash
# Custom LLM-as-a-Judge / RAGAS design benchmark
./scripts/run_experiments.sh benchmark single_agent gemini-2.5-flash true 1 devbench_benchmark
./scripts/run_experiments.sh benchmark read_agent   gemini-2.5-flash true 1 devbench_benchmark

# HumanEval / MBPP code benchmarks
./scripts/run_code_benchmark.sh single_agent gemini-2.5-flash true humaneval
./scripts/run_code_benchmark.sh read_agent   gemini-2.5-flash true humaneval
./scripts/run_code_benchmark.sh single_agent gemini-2.5-flash true mbpp
./scripts/run_code_benchmark.sh read_agent   gemini-2.5-flash true mbpp
```

Repeat with the OpenAI model to reproduce the second RQ1 comparison. Each invocation appends a
new experiment row to `runs/benchmark_runs/metrics.json` / `runs/code_benchmark_runs/metrics.json`;
`scripts/export_experiments.sh` exports these into the flat CSVs consumed by the notebook (see
that script's header for usage — it wraps `dvc exp show --csv`).

### RQ2 — RAG vs. no-RAG

```bash
# RAG using the general requirements corpus (datasets/promise, datasets/pure ->
# datasets/preprocessed/requirements_index.faiss)
./scripts/run_experiments.sh benchmark read_agent gemini-2.5-flash true  1 requirements
./scripts/run_experiments.sh benchmark read_agent gemini-2.5-flash false 1 requirements

# RAG using the DevBench corpus (datasets/DevBench/benchmark_data ->
# datasets/preprocessed/devbench_benchmark_index.faiss)
./scripts/run_experiments.sh benchmark read_agent gemini-2.5-flash true  1 devbench_benchmark
./scripts/run_experiments.sh benchmark read_agent gemini-2.5-flash false 1 devbench_benchmark
```

Both prebuilt FAISS indexes (`datasets/preprocessed/*.faiss`) are included so RAG-enabled runs
work immediately. To rebuild an index from source instead of using the shipped one:

```bash
python -m src.rag.indexer            # requirements_index.faiss from datasets/promise + datasets/pure
python -m src.rag.devbench_indexer   # devbench_benchmark_index.faiss from datasets/DevBench
```

## Data provenance

| File(s) | Used by | Notes |
|---|---|---|
| `benchmark_runs/{single,read}_agent_benchmark_{gemini,openai}.csv` | RQ1 | Design-quality metrics, agent=single_agent vs read_agent |
| `benchmark_runs/{single,read}_agent_code_benchmark_{humaneval,mbpp}_{gemini,openai}.csv` | RQ1 | pass@1 / pass@1+ |
| `benchmark_runs/read_agent_benchmark_gemini_{rag,no_rag}.csv` | RQ2 | requirements-corpus RAG index |
| `benchmark_runs/read_agent_benchmark_gemini_{index,no_rag}.csv` | RQ2 | DevBench-corpus RAG index (`_index` = DevBench-indexed run) |
| `data/samples/{humaneval,mbpp}/*.jsonl` | RQ1 | Exact generation/sanitized-sample/eval-result triplets referenced by the `code.samples` column of the RQ1 code-benchmark CSVs above — not the full samples archive |
| `data/goldens/{single_agent,read_agent}/benchmark.json` | RQ1, RQ2 | Task prompts used by the `benchmark` DVC stage |
| `datasets/promise/`, `datasets/pure/` | RQ2 | Source corpus for the requirements RAG index |
| `datasets/DevBench/benchmark_data/` | RQ2 | Source corpus for the DevBench RAG index |
| `datasets/preprocessed/*.faiss`, `*_chunks.json` | RQ2 | Prebuilt FAISS indexes + chunk metadata, ready to use without rebuilding |

## What was intentionally left out

- `runs/`, `.dvc/cache` — large, regenerable run artifacts and the DVC cache; re-running the
  commands above regenerates them locally.
- Prompt-optimization (`train`/`eval` DVC stages) and per-sub-agent goldens
  (`collector_agent`, `analyzer_agent`, `specifier_agent`, `designer_agent`,
  `documenter_agent`) — these support prompt tuning, not RQ1/RQ2.
- `benchmark_runs/` CSVs and code-benchmark sample files tied to Claude Sonnet 4, gpt-oss:20b,
  or Ollama runs — those back the dissertation's RQ2/RQ4, not this package's RQ1/RQ2.
- Real API keys / `.env` — see `.env.example`.
