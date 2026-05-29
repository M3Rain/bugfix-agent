"""Thin wrappers around Ollama clients so the rest of the code is isolated
from langchain_ollama specifics."""
from langchain_ollama import ChatOllama, OllamaEmbeddings

CHAT_MODEL = "qwen2.5-coder:7b"
EMBED_MODEL = "nomic-embed-text"


def get_chat(temperature: float = 0.2) -> ChatOllama:
    return ChatOllama(model=CHAT_MODEL, temperature=temperature)


def get_embeddings() -> OllamaEmbeddings:
    return OllamaEmbeddings(model=EMBED_MODEL)