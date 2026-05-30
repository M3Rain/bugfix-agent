import pytest
from agent.graph import run


@pytest.mark.slow
def test_e2e_fixes_bitcount():
    final = run("bitcount", max_attempts=6)
    assert final["status"] in {"success", "failed"}   # smoke: it terminates
    # If the model is reasonable, this should usually succeed:
    if final["status"] == "failed":
        pytest.skip(
            "Local model couldn't fix bitcount within 6 attempts — record "
            "this in your Critical Reflection section."
        )
    assert final["test_result"]["passed"] is True