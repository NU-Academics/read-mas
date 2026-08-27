"""Retriever for the DevBench benchmark FAISS index."""

from .retriever import make_retriever
from .constants import DEVBENCH_BENCHMARK_FAISS_INDEX_NAME, DEVBENCH_BENCHMARK_CHUNKS_NAME

retrieve_devbench_context = make_retriever(
    DEVBENCH_BENCHMARK_FAISS_INDEX_NAME,
    DEVBENCH_BENCHMARK_CHUNKS_NAME,
)
