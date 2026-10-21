"""One synthetic provider request; never sends the candidate's resume or prints keys."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / '.env', override=False)

from app.agent import _llm_intent
import os

if __name__ == '__main__':
    if not os.getenv('OPENAI_API_KEY'):
        raise SystemExit('No OPENAI_API_KEY configured. Add it to .env, then rerun. No provider request was made.')
    result = _llm_intent('Find early-career React roles available in India.', [])
    if not result:
        raise SystemExit('Live tool call did not validate. Check provider billing, model access, key permissions and connectivity. No application was sent.')
    if result['intent'] != 'recommend' or not ('React' in result['skills'] or result.get('skill') == 'React'):
        raise SystemExit('Provider returned valid arguments but missed the requested React search. Review the routing prompt before release.')
    print(f"Live function call passed: intent={result['intent']}; model={os.getenv('OPENAI_MODEL', 'gpt-4o-mini')}. No personal resume data was sent.")
