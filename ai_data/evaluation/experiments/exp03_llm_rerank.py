"""실험 03: LLM 재정렬(rerank) — 실험 01(동의어 확장) 위에 1개만 추가

가설: 정답은 대부분 찾지만 순위가 낮다(첫 정답 4~5위가 8문항, MRR 0.52). 검색 후보를 넓게(15개) 뽑은 뒤
     질문과의 관련성을 LLM이 다시 매기면 정답이 위로 올라온다.
변경: core.search(top_k=15, 동의어 확장 검색어)로 후보 15개 → gpt-4o-mini(temperature 0)가 관련도 순으로
     번호를 다시 매김 → 상위 5개로 평가. 인덱스·임베딩·필터는 v13b 그대로. LLM 오류 시 원래 순서로 대체.
운영 지표도 함께 기록: 문항당 재정렬 지연(ms)과 입·출력 토큰.

실행 (ai_data 폴더, OpenAI 키 필요):
  python evaluation/experiments/exp03_llm_rerank.py --index data/indexes/v13b-the-new-avante
"""
import argparse, json, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(Path(__file__).resolve().parent))
from chageun_ai.core import search, evaluate, read_json, write_json  # noqa: E402
from exp01_query_synonyms import expand  # noqa: E402

POOL, TOP_K, SNIPPET = 15, 5, 500
SYSTEM = ('너는 차량 설명서·도로교통법 검색 결과를 평가하는 재정렬기다. 질문에 직접 답할 수 있는 근거'
          '(구체적인 값·조건·절차·조문)를 담은 문단일수록 앞에 둔다. 주제만 비슷하고 답이 없는 문단은 뒤로 보낸다. '
          '반드시 JSON {"order": [문단 번호, ...]} 형식으로, 받은 번호를 모두 한 번씩 관련도 높은 순으로 답한다.')


def rerank(llm, question, hits, log):
    passages = '\n\n'.join(f"[{i}] ({h['chunk']['metadata'].get('section') or h['chunk']['metadata'].get('article') or ''})\n"
                           f"{h['chunk']['text'][:SNIPPET]}" for i, h in enumerate(hits))
    t0 = time.perf_counter()
    try:
        res = llm.invoke([('system', SYSTEM), ('human', f'질문: {question}\n\n문단:\n{passages}')])
        order = [int(i) for i in json.loads(res.content)['order'] if 0 <= int(i) < len(hits)]
        usage = res.usage_metadata or {}
        ok = True
    except Exception as e:  # 실패해도 평가는 계속: 원래 순서 사용
        order, usage, ok = [], {}, False
        print('rerank failed:', question, type(e).__name__, file=sys.stderr)
    order = list(dict.fromkeys(order + list(range(len(hits)))))  # 빠진 번호는 원래 순서대로 뒤에
    log.append({'question': question, 'ok': ok, 'latency_ms': round((time.perf_counter() - t0) * 1000),
                'in_tok': usage.get('input_tokens', 0), 'out_tok': usage.get('output_tokens', 0)})
    return [hits[i] for i in order]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--index', required=True)
    p.add_argument('--cases', default=str(ROOT / 'evaluation/cases.json'))
    p.add_argument('--out-dir', default=str(ROOT / 'evaluation/results'))
    p.add_argument('--llm-model', default='gpt-4o-mini')
    args = p.parse_args()
    from dotenv import load_dotenv
    from langchain_openai import OpenAIEmbeddings, ChatOpenAI
    load_dotenv(ROOT.parent / '.env')
    cases = read_json(args.cases)['cases']
    for c in cases:  # 잠정 평가: draft 문항도 채점 (원본 파일은 그대로)
        c['status'] = 'reviewed'
    emb = OpenAIEmbeddings(model=read_json(Path(args.index) / 'manifest.json')['embedding_model'])
    llm = ChatOpenAI(model=args.llm_model, temperature=0).bind(response_format={'type': 'json_object'})
    vec = {c['id']: emb.embed_query(c['question']) for c in cases if c['category'] == 'rag'}

    def hits(c, k, rewrite):
        return search(args.index, vec[c['id']], c['filters'], k, query=rewrite(c['question']))
    log = []
    runs = {
        'baseline': evaluate(cases, lambda c: hits(c, c.get('top_k', 5), lambda q: q)),
        'exp01': evaluate(cases, lambda c: hits(c, c.get('top_k', 5), expand)),
        'pool15': evaluate(cases, lambda c: hits(c, POOL, expand)),  # 재정렬 상한(후보 15개 안에 정답이 있나)
        'exp03': evaluate(cases, lambda c: rerank(llm, c['question'], hits(c, POOL, expand), log)[:TOP_K]),
    }
    out = Path(args.out_dir)
    for name, r in runs.items():
        write_json(out / f'exp03_{name}.json', dict(r, index=args.index))
    write_json(out / 'exp03_rerank_ops.json', {'model': args.llm_model, 'pool': POOL, 'calls': log})
    print(f"{'지표':<12}" + ''.join(f'{n:>10}' for n in runs) + '   (pool15 = 후보 15개 기준 상한)')
    for k in ('hit_rate', 'mean_recall', 'mrr'):
        print(f'{k:<12}' + ''.join(f'{r[k]:>10.3f}' for r in runs.values()))
    rr = {n: {x['id']: x for x in r['results'] if x['status'] == 'evaluated'} for n, r in runs.items()}
    print('\n문항     첫 정답 순위(baseline -> exp01 -> exp03)')
    for cid in rr['baseline']:
        ranks = ['-' if rr[n][cid]['reciprocal_rank'] == 0 else str(round(1 / rr[n][cid]['reciprocal_rank']))
                 for n in ('baseline', 'exp01', 'exp03')]
        if len(set(ranks)) > 1:
            print(f'{cid:<8} ' + ' -> '.join(ranks))
    lat = sorted(x['latency_ms'] for x in log)
    print(f"\n재정렬 {len(log)}회 · 실패 {sum(not x['ok'] for x in log)}회 · 지연 평균 {sum(lat) // len(lat)}ms "
          f"/ 최대 {lat[-1]}ms · 토큰 평균 입력 {sum(x['in_tok'] for x in log) // len(log)} "
          f"/ 출력 {sum(x['out_tok'] for x in log) // len(log)}")


if __name__ == '__main__':
    main()
