"""Persistent Chroma store of Reflexion-style verbal lessons.

Each document is a single reflection string. Metadata records the bug name and
attempt number so we can debug what got written. Embeddings use Ollama's
nomic-embed-text via langchain_ollama, but we wrap that in a Chroma-compatible
embedding function so Chroma owns persistence."""
from __future__ import annotations
from pathlib import Path
import uuid
import chromadb
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings

from agent.llm import get_embeddings


class _OllamaEmbeddingFunction(EmbeddingFunction):
    def __init__(self) -> None:
        self._emb = get_embeddings()

    def __call__(self, input: Documents) -> Embeddings:
        return self._emb.embed_documents(list(input))


class ReflectionStore:
    def __init__(self, persist_dir: str = "memory_store") -> None:
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=persist_dir)
        self._col = self._client.get_or_create_collection(
            name="reflections",
            embedding_function=_OllamaEmbeddingFunction(),
        )

    def add(self, bug_name: str, reflection: str, attempt: int = 0) -> None:
        self._col.add(
            ids=[str(uuid.uuid4())],
            documents=[reflection],
            metadatas=[{"bug_name": bug_name, "attempt": attempt}],
        )

    def search(self, query: str, k: int = 3) -> list[str]:
        if self._col.count() == 0:
            return []
        res = self._col.query(query_texts=[query], n_results=min(k, self._col.count()))
        return res.get("documents", [[]])[0]