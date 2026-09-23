"""3.2-CLOSEOUT-A live characterization harness.

Walks the same wire sequence as tests/integration/test_full_pipeline_integration.py
and tests/e2e/test_e2e_happy_path_full_job_application.py, but drives it over plain
HTTP so it does NOT depend on the two test helpers -- which send the Cognito
`access_token` where the API Gateway authorizer accepts only the `id_token`, and
therefore 401 on every authenticated wire before any endpoint is reached.

Records what the deployed stack ACTUALLY did per wire. It asserts nothing and
fixes nothing; a failure is data, not an error.
"""

from __future__ import annotations

import base64
import json
import os
import sys
import time
import uuid

import requests

BASE = os.environ['API_BASE'].rstrip('/')
STACK = os.environ.get('STACK_LABEL', 'unknown')
TIMEOUT = 30

wires: list[dict] = []


def call(method, path, *, token=None, body=None, note=''):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    t0 = time.time()
    try:
        r = requests.request(method, f'{BASE}{path}', headers=headers, json=body, timeout=TIMEOUT)
        status, text = r.status_code, r.text
    except Exception as exc:  # network-level failure is also data
        status, text = None, f'EXCEPTION: {exc!r}'
    ms = int((time.time() - t0) * 1000)
    try:
        data = json.loads(text)
    except Exception:
        data = {}
    rec = {
        'wire': f'{method} {path}',
        'status': status,
        'ms': ms,
        'note': note,
        'response_excerpt': text[:400],
    }
    wires.append(rec)
    print(f'  {method:5} {path:45} -> {status} ({ms} ms) {note}', flush=True)
    return status, (data.get('data') if isinstance(data.get('data'), dict) else data), text


def poll(path, token, timeout_s, label):
    """Poll an async artifact to a terminal state. Records the terminal outcome."""
    deadline = time.time() + timeout_s
    last = None
    polls = 0
    while time.time() < deadline:
        st, data, _ = call('GET', path, token=token, note=f'[poll {label}]')
        polls += 1
        if st != 200:
            last = f'non-200 {st}'
            break
        state = str(data.get('status', '')).lower()
        last = state
        if state in ('completed', 'failed', 'error'):
            break
        time.sleep(5)
    wires.append({
        'wire': f'POLL {path}',
        'status': None,
        'ms': None,
        'note': f'{label} terminal_state={last} polls={polls}',
        'response_excerpt': '',
    })
    print(f'  POLL  {path:45} -> terminal={last} after {polls} polls', flush=True)
    return last


print(f'=== CHARACTERIZATION against {STACK} :: {BASE} ===', flush=True)

email = f'char-{uuid.uuid4().hex[:10]}@careervp.com'
password = 'SecureP@ss123!'

print('\n-- auth --', flush=True)
call('POST', '/auth/register', body={'email': email, 'password': password, 'name': 'Characterization'})
st, login, _ = call('POST', '/auth/login', body={'email': email, 'password': password})

id_token = login.get('id_token', '')
access_token = login.get('access_token', '')

# Record the authorizer's token-type behavior explicitly -- this is the F-AUTH finding.
print('\n-- authorizer token-type probe --', flush=True)
call('GET', '/users/me', token=access_token, note='[access_token -- what the test helpers send]')
call('GET', '/users/me', token=id_token, note='[id_token -- what the authorizer accepts]')

token = id_token

print('\n-- pipeline (LIVE contract shapes, not the stale helper shapes) --', flush=True)
# WorkExperience.company is a required str; a CV with no explicit employer makes the
# parser emit company=None and the handler 500s. Give it an unambiguous employer.
cv_text = (
    'Jane Doe\n'
    'Senior Backend Engineer\n'
    'jane.doe@example.com | London, UK\n\n'
    'EXPERIENCE\n'
    'Senior Backend Engineer, Acme Corporation (2021 - Present)\n'
    '  - Built Python APIs on AWS Lambda serving 2M requests/day.\n'
    '  - Designed DynamoDB single-table data models and CI pipelines.\n\n'
    'Backend Engineer, Globex Ltd (2018 - 2021)\n'
    '  - Delivered payment services in Python and PostgreSQL.\n\n'
    'SKILLS\nPython, AWS Lambda, DynamoDB, CI/CD\n\n'
    'EDUCATION\nBSc Computer Science, University of Manchester, 2018\n'
)

# The helpers send {text_content} / {file_content,file_type}; cv_upload_handler only
# injects the authenticated user_id for the {cv_content,file_name} shape, so the helper
# shapes fail CVParseRequest on a missing user_id. Use the live contract shape.
# file_type set => cv_content is routed to file_content and must be base64.
# Omitting it routes cv_content to text_content as plain text.
st, cv, _ = call('POST', '/users/me/cv', token=token,
                 body={'cv_content': cv_text, 'file_name': 'jane-doe-cv.txt'},
                 note='[live CVUploadRequest shape, text path]')
cv_id = cv.get('cv_id') or cv.get('id') or (cv.get('user_cv') or {}).get('cv_id')

# JobCreateRequest requires title/company_name/description -- the helpers send
# company/job_description (and position/description), neither of which validates.
# `url` is BOTH required and live-fetched for reachability, so it must be a real URL.
st, job, _ = call('POST', '/jobs', token=token, body={
    'title': 'Senior Backend Engineer',
    'company_name': 'Integration Labs',
    'description': 'Build secure backend APIs, queues, and CI guardrails. '
                   'Requires Python, AWS Lambda, DynamoDB, and CI/CD experience.',
    'url': 'https://example.com/',
}, note='[live JobCreateRequest shape, reachable url]')
job_id = job.get('job_id') or job.get('id')
print(f'  cv_id={cv_id}  job_id={job_id}', flush=True)

# CompanyResearchRequest requires job_id; the helpers send {domain}.
call('POST', '/company-research/fetch', token=token,
     body={'job_id': job_id, 'company_name': 'Integration Labs'},
     note='[live CompanyResearchRequest shape]')

# /gap-analysis/questions runs the model synchronously and lands at ~28-29s against the
# API Gateway 29s integration cap, so it intermittently 504s. Retry so a timeout does not
# silently empty the whole downstream chain -- the flakiness itself is recorded as a finding.
questions: list = []
for attempt in range(1, 4):
    st, gapq, _ = call('POST', '/gap-analysis/questions', token=token,
                       body={'cv_id': cv_id, 'job_id': job_id},
                       note=f'[attempt {attempt}/3 -- 29s API GW cap]')
    if st == 200 and isinstance(gapq.get('questions'), list) and gapq['questions']:
        questions = gapq['questions']
        break
print(f'  gap questions returned: {len(questions)}', flush=True)

items = [
    {'question_id': str(q.get('question_id') or q.get('id')),
     'response': 'Characterization response describing measurable impact and STAR evidence.'}
    for q in questions[:10] if isinstance(q, dict) and (q.get('question_id') or q.get('id'))
]
gap_ids = []
if items:
    st, gr, _ = call('POST', f'/jobs/{job_id}/gap-responses', token=token,
                     body={'cv_id': cv_id, 'job_id': job_id, 'responses': items})
    v = gr.get('gap_response_ids') or gr.get('response_ids') or gr.get('ids')
    gap_ids = [str(x) for x in v] if isinstance(v, list) and v else [i['question_id'] for i in items]
print(f'  gap_response_ids: {len(gap_ids)}', flush=True)

vpr_id = None
st, vpr, _ = call('POST', '/vpr/generate', token=token,
                  body={'cv_id': cv_id, 'job_id': job_id, 'gap_response_ids': gap_ids})
if st == 202:
    vpr_id = vpr.get('request_id') or vpr.get('vpr_id') or vpr.get('id')
    poll(f'/vpr/{vpr_id}/status', token, 300, 'vpr')

if vpr_id:
    st, cvt, _ = call('POST', '/cv-tailoring/generate', token=token,
                      body={'cv_id': cv_id, 'job_id': job_id, 'vpr_id': vpr_id})
    if st == 202:
        poll(f"/cv-tailoring/{cvt.get('request_id') or cvt.get('id')}/status", token, 300, 'cv-tailoring')

    st, cl, _ = call('POST', '/cover-letter/generate', token=token, body={
        'cv_id': cv_id, 'job_id': job_id, 'vpr_id': vpr_id,
        'gap_response_ids': gap_ids, 'company_research_id': 'placeholder-research-id',
    })
    if st == 202:
        poll(f"/cover-letter/{cl.get('request_id') or cl.get('id')}/status", token, 300, 'cover-letter')

print('\n-- interview-prep: the D-H4/P-01 v3.0.0 contract wire --', flush=True)

# The FIXED fixture shape: application identity present.
st, ip, _ = call('POST', '/interview-prep/generate', token=token,
                 body={'application_id': job_id, 'vpr_id': vpr_id, 'gap_response_ids': gap_ids},
                 note='[FIXED fixture shape: application_id present]')
if st == 202:
    ip_id = ip.get('request_id') or ip.get('id')
    poll(f'/interview-prep/{ip_id}/status', token, 300, 'interview-prep')

# The OLD broken fixture shape: no application identity. v3.0.0 must refuse with 400.
call('POST', '/interview-prep/generate', token=token,
     body={'vpr_id': vpr_id, 'gap_response_ids': gap_ids},
     note='[OLD broken shape: no application identity -- v3.0.0 expects HTTP 400]')

out = {
    'step': '3.2-CLOSEOUT-A',
    'stack': STACK,
    'api_base': BASE,
    'user_email': email,
    'cv_id': cv_id,
    'job_id': job_id,
    'vpr_id': vpr_id,
    'wires': wires,
}
path = sys.argv[1]
with open(path, 'w') as fh:
    json.dump(out, fh, indent=2)
print(f'\nwrote {path}', flush=True)
