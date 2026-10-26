"""End-to-end evaluation: runs each case through the same rag_query the server uses.

Retrieval-only metrics stay in core.evaluate. Here each case is checked on what the api-server
receives: status, action, cited pages, required facts in the answer, and stability across runs.
"""
from __future__ import annotations
import re
from collections import Counter


def build_request(case, run):
    extra = case.get('request', {})
    return {'request_id': f"{case['id']}-{run}", 'conversation_id': f"eval-{case['id']}", 'question': case['question'],
            'vehicle': extra.get('vehicle'), 'location': extra.get('location'), 'history': extra.get('history', []),
            'destination': extra.get('destination'),
            'maintenance': extra.get('maintenance') or {'lookup_status': 'not_requested', 'items': [], 'records': []}}


def compact(text):
    return re.sub(r'\s+', '', text or '')


def check(case, response, retrieved_ids):
    """Each check is True/False, or None when the case does not define it."""
    expected_action = case.get('expected_action')
    action = response.get('action') or {}
    pages = [s.get('page') for s in response.get('sources', [])]
    facts, chunks, sources = case.get('required_facts'), case.get('expected_chunk_ids'), case.get('expected_sources')
    return {
        'status': response.get('status') in case['expected_status'],
        # Expected action fields are a subset of the returned action.
        'action': (action == {} if expected_action is None
                   else all(action.get(k) == v for k, v in expected_action.items())),
        'retrieval': bool(set(chunks) & set(retrieved_ids)) if chunks and 'answered' in case['expected_status'] else None,
        'source': (any(p in sources for p in pages) if sources and response.get('status') == 'answered' else None),
        'facts': (all(compact(f) in compact(response.get('answer')) for f in facts)
                  if facts and response.get('status') == 'answered' else None),
    }


def evaluate_pipeline(cases, ask, runs=1, include_drafts=False):
    """ask(request) -> (response, retrieved chunk ids). Drafts are skipped unless include_drafts."""
    results = []
    for case in cases:
        if case.get('status') != 'reviewed' and not include_drafts:
            results.append({'id': case['id'], 'status': 'pending'})
            continue
        attempts = []
        for run in range(runs):
            response, retrieved = ask(build_request(case, run))
            checks = check(case, response, retrieved)
            attempts.append({'passed': all(v is not False for v in checks.values()), 'checks': checks,
                             'status': response.get('status'), 'action': response.get('action'),
                             'pages': [s.get('page') for s in response.get('sources', [])],
                             'answer': response.get('answer'), 'retrieved_ids': retrieved})
        statuses = Counter(a['status'] for a in attempts)
        results.append({'id': case['id'], 'category': case.get('category'), 'question': case['question'],
                        'status': 'evaluated', 'review': case.get('status'),
                        'pass_rate': sum(a['passed'] for a in attempts) / runs,
                        'stable': statuses.most_common(1)[0][1] == runs, 'attempts': attempts})
    scored = [r for r in results if r['status'] == 'evaluated']

    def rate(check_name):
        values = [a['checks'][check_name] for r in scored for a in r['attempts'] if a['checks'][check_name] is not None]
        return sum(values) / len(values) if values else None

    by_category = {}
    for r in scored:
        by_category.setdefault(r['category'], []).append(r['pass_rate'])
    return {
        'total': len(results), 'evaluated': len(scored), 'pending': len(results) - len(scored), 'runs': runs,
        'provisional': any(r['review'] != 'reviewed' for r in scored),
        'pass_rate': sum(r['pass_rate'] for r in scored) / len(scored) if scored else None,
        'unstable': [r['id'] for r in scored if not r['stable']],
        'failed': [r['id'] for r in scored if r['pass_rate'] < 1],
        'check_rates': {name: rate(name) for name in ('status', 'action', 'retrieval', 'source', 'facts')},
        'by_category': {k: sum(v) / len(v) for k, v in sorted(by_category.items())},
        'results': results,
    }
