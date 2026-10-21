"""Unit/HTTP tests never use a developer's real provider credentials."""
import pytest


@pytest.fixture(autouse=True)
def isolated_provider_environment(monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER', 'none')
    for name in ('GEMINI_API_KEY', 'OPENAI_API_KEY', 'GEMINI_MODEL', 'OPENAI_MODEL'):
        monkeypatch.delenv(name, raising=False)
