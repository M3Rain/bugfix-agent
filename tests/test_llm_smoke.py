"""Smoke test: requires Ollama running locally with the two models pulled.
Marked slow so unit-test runs can skip it with `pytest -m 'not slow'`."""
import pytest
from agent.llm import get_chat, get_embeddings


@pytest.mark.slow
def test_chat_responds():
    chat = get_chat()
    msg = chat.invoke("Reply with the single word: pong")
    assert "pong" in msg.content.lower()


@pytest.mark.slow
def test_embeddings_produce_vector():
    emb = get_embeddings()
    v = emb.embed_query("hello world")
    assert isinstance(v, list)
    assert len(v) > 100   # nomic-embed-text outputs 768 dims