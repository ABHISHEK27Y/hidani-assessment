"""One synthetic provider request; never sends the candidate's resume or prints keys."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / '.env', override=False)

from app.agent import _llm_intent, llm_status

if __name__ == '__main__':
    status = llm_status()
    if not status['llm_configured']:
        variable = 'GEMINI_API_KEY' if status['llm_provider'] == 'gemini' else 'OPENAI_API_KEY'
        raise SystemExit(f'Provider {status["llm_provider"]} is not configured. Set {variable} in .env, then rerun. No provider request was made.')
    result = _llm_intent('Find early-career React roles available in India.', [])
    if not result:
        raise SystemExit('Live tool call did not validate. Check the selected provider key, quota, model access and connectivity. No application was sent.')
    if result['intent'] != 'recommend' or not ('React' in result['skills'] or result.get('skill') == 'React'):
        raise SystemExit('Provider returned valid arguments but missed the requested React search. Review the routing prompt before release.')
    print(f"Live function call passed: provider={status['llm_provider']}; intent={result['intent']}; model={status['llm_model']}. No personal resume data was sent.")
