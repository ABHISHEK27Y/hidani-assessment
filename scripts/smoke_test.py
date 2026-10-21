"""Exercise a running deployment with synthetic data and remove its test workspace."""
import argparse
import uuid
from urllib.parse import urlparse

import fitz
import httpx


def verify(base_url):
    url = urlparse(base_url)
    if url.username or url.password or (url.scheme != 'https' and not (url.scheme == 'http' and url.hostname in {'127.0.0.1', 'localhost', '::1'})):
        raise ValueError('Use HTTPS for a public deployment, or HTTP on localhost.')
    sid = str(uuid.uuid4())
    count = 0
    def check(condition, label):
        nonlocal count
        if not condition:
            raise AssertionError(label)
        count += 1
        print(f'PASS {label}', flush=True)
    with fitz.open() as pdf:
        page = pdf.new_page()
        page.insert_text((30, 40), 'Demo Candidate\ndemo@example.test\nWORK EXPERIENCE\nSoftware Engineering Intern June 2026 - August 2026\nBuilt Python and React APIs.\nEDUCATION\nB.Tech Computer Science\nPROJECTS\nCloudCanvas\nBuilt Docker tooling.\nTECHNICAL SKILLS\nPython React TypeScript AWS Docker Git')
        resume = pdf.tobytes()
    with httpx.Client(base_url=base_url.rstrip('/'), timeout=30, follow_redirects=False) as client:
        def get(path, **kwargs):
            response = client.get(path, **kwargs); response.raise_for_status(); return response
        def post(path, **kwargs):
            response = client.post(path, **kwargs); response.raise_for_status(); return response.json()
        try:
            check(get('/health').json()['ok'], 'Readiness')
            check('Orbit' in get('/').text, 'Workspace page')
            check('/api/chat' in get('/openapi.json').json()['paths'], 'API schema')
            check('swagger-ui' in get('/docs').text, 'API docs response')
            parsed = post('/api/resume', data={'session_id': sid}, files={'file': ('demo.pdf', resume, 'application/pdf')})
            check(parsed['profile']['name'] == 'Demo Candidate', 'PDF parsing')
            check(parsed['jobs'] and parsed['total'] > 0, 'Recommendations')
            job_id = parsed['jobs'][0]['id']
            check(get('/api/jobs/' + job_id).json()['description'], 'Job detail')
            filtered = post('/api/chat', json={'session_id': sid, 'message': 'remote React jobs in India'})
            check(filtered['jobs'] and all('React' in job['skills'] and job['remote'] for job in filtered['jobs']), 'Conversational refinement')
            first = post('/api/applications', json={'session_id': sid, 'job_id': job_id})
            again = post('/api/applications', json={'session_id': sid, 'job_id': job_id})
            check(again['application']['duplicate'], 'Duplicate application protection')
            check(first['application']['status'] in {'awaiting_submission', 'submitted'}, 'Application state')
            records = get('/api/applications', params={'session_id': sid}).json()['applications']
            check(len(records) == 1, 'Tracker')
            restored = get('/api/bootstrap', params={'session_id': sid}).json()
            check(restored['profile'] and restored['history'], 'Restored workspace')
        finally:
            response = client.delete('/api/session/' + sid)
            response.raise_for_status()
        check(not get('/api/bootstrap', params={'session_id': sid}).json()['profile'], 'Workspace reset')
        # Bootstrap creates an empty row; clean that as well.
        client.delete('/api/session/' + sid).raise_for_status()
    print(f'{count} deployment smoke checkpoints passed. No real employer application was sent.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='http://127.0.0.1:8000')
    verify(parser.parse_args().base_url)
