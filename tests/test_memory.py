import pytest
from agent.memory import ReflectionStore


@pytest.mark.slow
def test_write_and_retrieve(tmp_path):
    store = ReflectionStore(persist_dir=str(tmp_path / "chroma"))
    store.add(
        bug_name="bitcount",
        reflection="When recursing on bit counts, check the base case is n==0 not n<=0.",
    )
    store.add(
        bug_name="gcd",
        reflection="Euclidean GCD requires abs() when inputs may be negative.",
    )
    hits = store.search(query="recursive base case bug", k=2)
    assert len(hits) == 2
    assert any("base case" in h for h in hits)


@pytest.mark.slow
def test_empty_store_returns_empty_list(tmp_path):
    store = ReflectionStore(persist_dir=str(tmp_path / "chroma"))
    assert store.search("anything", k=3) == []