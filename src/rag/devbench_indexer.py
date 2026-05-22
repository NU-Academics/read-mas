"""Index non-input sections of DevBench benchmark PRD files into a separate FAISS index."""

import json
import re
import os
from pathlib import Path

import faiss
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger

from .constants import (
  BASE_REQUIREMENTS_PATH,
  DEVBENCH_BENCHMARK_CHUNKS_NAME,
  DEVBENCH_BENCHMARK_FAISS_INDEX_NAME,
  DEVBENCH_BENCHMARK_PATH,
  DEVBENCH_INPUT_SECTIONS,
  PURE_DOCS_CHUNK_OVERLAP,
  PURE_DOCS_CHUNK_SIZE,
)
from .embed_utils import embed_chunks

load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env", override=False)


def _extract_non_input_sections(prd_text: str) -> str:
  """Return PRD content from sections NOT used in extract_requirements_text()."""
  heading_pat = re.compile(r'^(#{1,6})\s+(.*)$', re.MULTILINE)
  matches = list(heading_pat.finditer(prd_text))
  sections = []
  for i, match in enumerate(matches):
    heading = match.group(2).strip()
    if heading.lower() not in DEVBENCH_INPUT_SECTIONS:
      start = match.end()
      end = matches[i + 1].start() if i + 1 < len(matches) else len(prd_text)
      body = prd_text[start:end].strip()
      if body:
        sections.append(f"## {heading}\n{body}")
  return "\n\n".join(sections)


def _load_benchmark_projects() -> list[dict]:
  """Load PRD files for benchmark projects listed in benchmark.json."""
  benchmark_json = Path("data/goldens/read_agent/benchmark.json")
  if not benchmark_json.exists():
    logger.error(f"Benchmark golden file not found: {benchmark_json}")
    return []
  with open(benchmark_json) as f:
    project_names = {g["source_file"] for g in json.load(f)}

  projects = []
  for lang_dir in DEVBENCH_BENCHMARK_PATH.iterdir():
    if not lang_dir.is_dir():
      continue
    for project_dir in lang_dir.iterdir():
      if not project_dir.is_dir() or project_dir.name not in project_names:
        continue
      prd_path = project_dir / "PRD.md"
      if prd_path.exists():
        projects.append({
          "name": project_dir.name,
          "language": lang_dir.name,
          "prd": prd_path.read_text(encoding="utf-8"),
        })
  return projects


def _chunk_devbench_prds() -> list[dict]:
  """Chunk non-input sections from the 14 benchmark PRDs."""
  projects = _load_benchmark_projects()
  splitter = RecursiveCharacterTextSplitter(
    chunk_size=PURE_DOCS_CHUNK_SIZE, chunk_overlap=PURE_DOCS_CHUNK_OVERLAP
  )
  chunks = []
  for project in projects:
    non_input_text = _extract_non_input_sections(project["prd"])
    if not non_input_text.strip():
      logger.warning(f"No non-input sections found for {project['name']}")
      continue
    for i, chunk in enumerate(splitter.split_text(non_input_text)):
      chunks.append({
        "source": "devbench_prd",
        "source_id": project["name"],
        "language": project["language"],
        "chunk_index": i,
        "chunk": chunk,
      })
  logger.info(f"DevBench PRDs: {len(chunks)} chunks from {len(projects)} projects")
  return chunks


def index_devbench_benchmark():
  """Build FAISS index from DevBench benchmark PRD non-input sections."""
  from utils import setup_logging, get_run_id

  setup_logging(get_run_id(), "devbench_indexer")
  logger.info("Building DevBench benchmark FAISS index...")

  chunks = _chunk_devbench_prds()
  if not chunks:
    logger.error("No chunks generated. Aborting.")
    return

  logger.info(f"Embedding {len(chunks)} chunks...")
  embeddings = embed_chunks(chunks)

  dimension = embeddings.shape[1]
  index = faiss.IndexFlatL2(dimension)
  index.add(embeddings)
  logger.info(f"FAISS index: {index.ntotal} vectors, dimension={dimension}")

  BASE_REQUIREMENTS_PATH.mkdir(parents=True, exist_ok=True)
  faiss.write_index(index, str(BASE_REQUIREMENTS_PATH / DEVBENCH_BENCHMARK_FAISS_INDEX_NAME))
  with open(BASE_REQUIREMENTS_PATH / DEVBENCH_BENCHMARK_CHUNKS_NAME, "w") as f:
    json.dump(chunks, f, indent=2)
  logger.info(f"Saved to {BASE_REQUIREMENTS_PATH / DEVBENCH_BENCHMARK_FAISS_INDEX_NAME}")


if __name__ == "__main__":
  index_devbench_benchmark()
