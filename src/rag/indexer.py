"""Index multi-source requirements datasets into a FAISS vector database.

Sources:
  - PROMISE: Labeled requirements from CSV (256-char chunks)
  - PURE XML: Structured SRS sections (natural section boundaries)
  - PURE docs: PDF/DOCX/HTML SRS documents (512-char chunks)
  - Knowledge base: RE methodology knowledge (heading-based splits)
"""

from dotenv import load_dotenv
import json
from pathlib import Path
import re
import os

import faiss
from google import genai
import numpy as np
import pandas as pd
import pdfplumber
import xmltodict
from docx import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from loguru import logger
from utils import setup_logging, get_run_id

from .constants import (
    BASE_REQUIREMENTS_PATH,
    FAISS_INDEX_NAME,
    GEMINI_EMBEDDING_MODEL,
    PROMISE_CHUNK_OVERLAP,
    PROMISE_CHUNK_SIZE,
    PROMISE_PATH,
    PURE_DOCS_CHUNK_OVERLAP,
    PURE_DOCS_CHUNK_SIZE,
    PURE_DOCS_HOLDOUT,
    PURE_DOCS_PATH,
    PURE_XML_PATH,
    REQUIREMENT_CHUNKS_NAME,
    EMBED_BATCH_SIZE,
)

load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env", override=False)

def _get_doc_base_name(filename: str) -> str:
  """Extract base name without extension for holdout matching.

  Handles .doc/.docx pairs by stripping the extension.
  """
  stem = filename
  for ext in [".docx", ".doc", ".pdf", ".html", ".rtf"]:
    if stem.endswith(ext):
      stem = stem[: -len(ext)]
      break
  return stem.strip()


def _chunk_promise() -> list[dict]:
  """Load and chunk PROMISE requirements by project."""
  if not PROMISE_PATH.exists():
    logger.warning(f"PROMISE CSV not found at {PROMISE_PATH}")
    return []

  df = pd.read_csv(PROMISE_PATH)

  tag_map = {
      "IsFunctional": "Functional",
      "IsQuality": "Quality",
      "Availability (A)": "Availability",
      "Fault Tolerance (FT)": "FaultTolerance",
      "Legal (L)": "Legal",
      "Look & Feel (LF)": "LookAndFeel",
      "Maintainability (MN)": "Maintainability",
      "Operability (O)": "Operability",
      "Performance (PE)": "Performance",
      "Portability (PO)": "Portability",
      "Scalability (SC)": "Scalability",
      "Security (SE)": "Security",
      "Usability (US)": "Usability",
      "Other (OT)": "Other",
  }

  def build_tags(row):
    tags = ["Functional" if row["IsFunctional"] == 1 else "NonFunctional"]
    for col, friendly in tag_map.items():
      if col != "IsFunctional" and row.get(col) == 1:
        tags.append(friendly)
    return tags

  df["text_clean"] = df["RequirementText"].str.strip("'")
  df["tags"] = df.apply(build_tags, axis=1)
  df["req_metadata"] = df["text_clean"] + ": " + df["tags"].apply(",".join)

  grouped = df.groupby("ProjectID")["req_metadata"].apply(" | ".join)

  splitter = RecursiveCharacterTextSplitter(
      chunk_size=PROMISE_CHUNK_SIZE, chunk_overlap=PROMISE_CHUNK_OVERLAP
  )

  chunks = []
  for project_id, text in grouped.items():
    for i, chunk in enumerate(splitter.split_text(text)):
      chunks.append({
          "source": "promise",
          "source_id": f"promise_{project_id}",
          "chunk_index": i,
          "chunk": chunk,
      })

  logger.info(f"PROMISE: {len(chunks)} chunks from {grouped.shape[0]} projects")
  return chunks


def _chunk_pure_xml() -> list[dict]:
  """Parse PURE XML files and extract sections as chunks."""
  if not PURE_XML_PATH.exists():
    logger.warning(f"PURE XML path not found at {PURE_XML_PATH}")
    return []

  chunks = []
  for xml_file in sorted(PURE_XML_PATH.glob("*.xml")):
    try:
      with open(xml_file, "r", encoding="utf-8") as f:
        doc = xmltodict.parse(f.read())

      def extract_sections(obj, sections=None):
        if sections is None:
          sections = []
        if isinstance(obj, dict):
          if "title" in obj and "text_body" in obj:
            title = obj["title"].strip() if isinstance(obj["title"], str) else ""
            body = obj["text_body"].strip() if isinstance(obj["text_body"], str) else ""
            if body:
              sections.append(f"{title}\n{body}" if title else body)
          if "p" in obj:
            p = obj["p"]
            if isinstance(p, list):
              for item in p:
                extract_sections(item, sections)
            elif isinstance(p, dict):
              extract_sections(p, sections)
          for k, v in obj.items():
            if k not in ("p", "title", "text_body"):
              extract_sections(v, sections)
        elif isinstance(obj, list):
          for item in obj:
            extract_sections(item, sections)
        return sections

      sections = extract_sections(doc)
      source_id = xml_file.stem

      for i, section in enumerate(sections):
        if len(section.strip()) > 20:
          chunks.append({
              "source": "pure_xml",
              "source_id": source_id,
              "chunk_index": i,
              "chunk": section.strip(),
          })
    except Exception as e:
      logger.error(f"Error parsing {xml_file.name}: {e}")

  logger.info(f"PURE XML: {len(chunks)} chunks from {len(list(PURE_XML_PATH.glob('*.xml')))} files")
  return chunks


def _extract_text_from_pdf(filepath) -> str:
  """Extract text from a PDF file using pdfplumber."""
  text_parts = []
  try:
    with pdfplumber.open(filepath) as pdf:
      for page in pdf.pages:
        page_text = page.extract_text()
        if page_text:
          text_parts.append(page_text)
  except Exception as e:
    logger.error(f"Error extracting PDF {filepath.name}: {e}")
  return "\n\n".join(text_parts)


def _extract_text_from_docx(filepath) -> str:
  """Extract text from a DOCX file using python-docx."""
  try:
    doc = Document(str(filepath))
    return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
  except Exception as e:
    logger.error(f"Error extracting DOCX {filepath.name}: {e}")
    return ""


def _extract_text_from_html(filepath) -> str:
  """Extract text from an HTML file by stripping tags."""
  try:
    content = filepath.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"<[^>]+>", " ", content)
    text = re.sub(r"\s+", " ", text).strip()
    return text
  except Exception as e:
    logger.error(f"Error extracting HTML {filepath.name}: {e}")
    return ""


def _chunk_pure_docs() -> list[dict]:
  """Extract and chunk PURE requirement documents (PDF/DOCX/HTML), excluding holdout set."""
  if not PURE_DOCS_PATH.exists():
    logger.warning(f"PURE docs path not found at {PURE_DOCS_PATH}")
    return []

  splitter = RecursiveCharacterTextSplitter(
      chunk_size=PURE_DOCS_CHUNK_SIZE, chunk_overlap=PURE_DOCS_CHUNK_OVERLAP
  )

  chunks = []
  indexed_count = 0
  skipped_count = 0

  for filepath in sorted(PURE_DOCS_PATH.iterdir()):
    base_name = _get_doc_base_name(filepath.name)

    # Skip holdout documents
    if base_name in PURE_DOCS_HOLDOUT:
      skipped_count += 1
      continue


    ext = filepath.suffix.lower()
    if ext == ".pdf":
      text = _extract_text_from_pdf(filepath)
    elif ext == ".docx":
      text = _extract_text_from_docx(filepath)
    elif ext == ".html":
      text = _extract_text_from_html(filepath)
    else:
      continue

    if len(text.strip()) < 100:
      logger.warning(f"Very short extraction from {filepath.name}: {len(text)} chars")
      continue

    source_id = filepath.stem
    for i, chunk in enumerate(splitter.split_text(text)):
      chunks.append({
          "source": "pure_doc",
          "source_id": source_id,
          "chunk_index": i,
          "chunk": chunk,
      })
    indexed_count += 1

  logger.info(
      f"PURE docs: {len(chunks)} chunks from {indexed_count} docs "
      f"({skipped_count} held out for goldens)"
  )
  return chunks


def _batch_chunks(seq, size):
  """Splits chunks into multiple batches based on the batch size."""
  for pos in range(0, len(seq), size):
    yield seq[pos:pos+size]

def _embed_chunks(chunks: list[dict]) -> np.ndarray:
  """Embed all chunks using Ollama."""
  emb_list = []
  texts = [c["chunk"] for c in chunks]
  
  client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
  for batch in _batch_chunks(texts, EMBED_BATCH_SIZE):
    res = client.models.embed_content(model=GEMINI_EMBEDDING_MODEL, contents=batch)
    emb_list.extend(res.embeddings)

  # Return a 2‑D float32 NumPy array
  return np.array([e.values for e in emb_list], dtype=np.float32)


def index_requirements():
  """Build multi-source FAISS index from all configured data sources."""
  
  setup_logging(get_run_id(), "rag_indexer")
  logger.info("Starting multi-source FAISS index build...")

  try:
    # Collect chunks from all sources
    all_chunks = []
    all_chunks.extend(_chunk_promise())
    all_chunks.extend(_chunk_pure_xml())
    all_chunks.extend(_chunk_pure_docs())

    if not all_chunks:
      logger.error("No chunks generated from any source. Aborting.")
      return

    # Log source distribution
    source_counts = {}
    for chunk in all_chunks:
      source_counts[chunk["source"]] = source_counts.get(chunk["source"], 0) + 1
    logger.info(f"Total chunks: {len(all_chunks)}")
    for source, count in sorted(source_counts.items()):
      logger.info(f"  {source}: {count} chunks")

    # Embed all chunks
    logger.info("Embedding chunks...")
    embeddings = _embed_chunks(all_chunks)

    # Build FAISS index
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    logger.info(f"FAISS index built: {index.ntotal} vectors, dimension={dimension}")

    # Save index and metadata
    BASE_REQUIREMENTS_PATH.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(BASE_REQUIREMENTS_PATH / FAISS_INDEX_NAME))

    with open(str(BASE_REQUIREMENTS_PATH / REQUIREMENT_CHUNKS_NAME), "w") as f:
      json.dump(all_chunks, f, indent=2)

    logger.info(
        f"Saved index to {BASE_REQUIREMENTS_PATH / FAISS_INDEX_NAME} "
        f"and chunks to {BASE_REQUIREMENTS_PATH / REQUIREMENT_CHUNKS_NAME}"
    )

  except Exception as e:
    logger.debug(f"Error while indexing RAG data in FAISS: {str(e)}")

if __name__ == "__main__":
  index_requirements()
