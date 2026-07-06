"""Test suite for secret redaction in OS observer."""

import os
import asyncio
from observers.os import inspect, _should_redact


def test_should_redact():
    """Test that secret keywords are correctly identified."""
    assert _should_redact("MY_SECRET_TOKEN") == True
    assert _should_redact("API_KEY") == True
    assert _should_redact("ANTHROPIC_API_KEY") == True
    assert _should_redact("DATABASE_PASSWORD") == True
    assert _should_redact("AUTH_TOKEN") == True
    assert _should_redact("GITHUB_ACCESS_TOKEN") == True
    assert _should_redact("USER") == False
    assert _should_redact("HOME") == False
    assert _should_redact("PATH") == False


async def test_env_var_redaction():
    """Test that environment variables with secrets are redacted."""
    os.environ["MY_SECRET_TOKEN"] = "abc123"
    os.environ["SAFE_VAR"] = "visible"

    result = await inspect()

    env_vars = result.get("environment_variables", {})

    if "MY_SECRET_TOKEN" in env_vars:
        assert env_vars["MY_SECRET_TOKEN"] == "[REDACTED]", \
            f"Secret token was not redacted: {env_vars['MY_SECRET_TOKEN']}"

    if "SAFE_VAR" in env_vars:
        assert env_vars["SAFE_VAR"] == "visible", \
            f"Safe variable was incorrectly redacted"

    del os.environ["MY_SECRET_TOKEN"]
    del os.environ["SAFE_VAR"]

    print("✓ Secret redaction test passed")


if __name__ == "__main__":
    asyncio.run(test_env_var_redaction())
    test_should_redact()
    print("All tests passed!")
