"""Constants for the RAG indexer and retriever."""

from pathlib import Path

BASE_REQUIREMENTS_PATH = Path("datasets/requirements")

CHUNK_SIZE = 256
CHUNK_OVERLAP = 32

OLLAMA_EMBEDDING_MODEL = "nomic-embed-text:latest"

GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"

FAISS_INDEX_NAME = "requirements_index.faiss"

REQUIREMENT_CHUNKS_NAME = "requirement_chunks.json"

RAG_TOP_K = 3
