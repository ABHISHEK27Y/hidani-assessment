import json
import uuid
from types import SimpleNamespace

import pytest

from app import agent, store


def fake_response(arguments):
    call = SimpleNamespace(function=SimpleNamespace(name='route_job_request', arguments=json.dumps(arguments)))
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=[call]))])


def test_gemini_uses_its_own_key_endpoint_and_validated_tools(monkeypatch):
    import openai
    monkeypatch.delenv('LLM_PROVIDER', raising=False)
    monkeypatch.setenv('GEMINI_API_KEY', 'synthetic-gemini-key')
    monkeypatch.setenv('OPENAI_API_KEY', 'synthetic-other-key')
    captured = {}
    def create(**kwargs):
        captured['request'] = kwargs
        return fake_response({'intent': 'recommend', 'skills': ['React'], 'location': 'India'})
    def client(**kwargs):
        captured['client'] = kwargs
        return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(openai, 'OpenAI', client)
    result = agent._llm_intent('Find React positions in India.', [])
    assert result['skills'] == ['React'] and result['location'] == 'India'
    assert captured['client']['api_key'] == 'synthetic-gemini-key'
    assert captured['client']['base_url'] == agent.GEMINI_BASE_URL
    assert captured['client']['max_retries'] == 1
    assert captured['client']['timeout'] == 25
    assert captured['request']['model'] == 'gemini-3.8-flash'
    assert 'strict' not in captured['request']['tools'][0]['function']
    assert 'synthetic-' not in json.dumps(agent.llm_status())


def test_missing_gemini_key_does_not_use_openai_key(monkeypatch):
    import openai
    monkeypatch.setenv('LLM_PROVIDER', 'gemini')
    monkeypatch.delenv('GEMINI_API_KEY', raising=False)
    monkeypatch.setenv('OPENAI_API_KEY', 'synthetic-other-key')
    monkeypatch.setattr(openai, 'OpenAI', lambda **_: pytest.fail('No provider client should be created'))
    assert agent._llm_intent('Something ambiguous', []) is None
    assert not agent.llm_status()['llm_configured']


def test_gemini_quota_failure_uses_local_rules_without_switching_provider(tmp_path, monkeypatch):
    import openai
    monkeypatch.setenv('LLM_PROVIDER', 'gemini')
    monkeypatch.setenv('GEMINI_API_KEY', 'synthetic-gemini-key')
    monkeypatch.setenv('OPENAI_API_KEY', 'synthetic-other-key')
    monkeypatch.setattr(store, 'DB_PATH', tmp_path / 'quota.db')
    store.init_db()
    calls = []
    def limited(**kwargs):
        calls.append(kwargs['base_url'])
        raise RuntimeError('Synthetic quota failure')
    monkeypatch.setattr(openai, 'OpenAI', limited)
    result = agent.respond(str(uuid.uuid4()), 'Something ambiguous')
    assert result['router'] == 'rules' and result['reply']
    assert calls == [agent.GEMINI_BASE_URL]


def test_gemini_arguments_still_reject_unexpected_fields(monkeypatch):
    import openai
    monkeypatch.setenv('LLM_PROVIDER', 'gemini')
    monkeypatch.setenv('GEMINI_API_KEY', 'synthetic-gemini-key')
    fake = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **_: fake_response({'intent': 'apply', 'reference': 1, 'bypass_confirmation': True}))))
    monkeypatch.setattr(openai, 'OpenAI', lambda **_: fake)
    assert agent._llm_intent('Something ambiguous', []) is None


def test_explicit_offline_mode_does_not_call_any_provider(monkeypatch):
    monkeypatch.setenv('LLM_PROVIDER', 'none')
    monkeypatch.setenv('GEMINI_API_KEY', 'synthetic-gemini-key')
    assert not agent.llm_status()['llm_configured']
    assert agent._llm_intent('Something ambiguous', []) is None
