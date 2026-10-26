"""실험 01: BM25 검색어 동의어 확장 (변경 1개만)

가설: 사용자 표현과 문서 표현이 달라 키워드 검색이 놓친다.
  - "달라/차이" ↔ 법 조문의 정의 표현 "~란 … 말한다" (CG-05)
  - "교환/갈아" ↔ 설명서의 "교체", "주기" ↔ "정기 점검" (CG-10, CG-15)
변경: BM25에 넣는 검색어 뒤에 동의어를 덧붙인다. 임베딩 질의·필터·top_k·인덱스는 그대로.
원본 코드(core.py)는 수정하지 않고 search(query=...) 인자만 바꿔 같은 평가셋으로 전후를 잰다.

실행 (ai_data 폴더, OpenAI 키 필요):
  python evaluation/experiments/exp01_query_synonyms.py --index data/indexes/v13b-the-new-avante
"""
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from chageun_ai.core import search, evaluate, read_json, write_json  # noqa: E402

SYNONYMS = {'교환': '교체', '갈아': '교체', '주기': '정기 점검', '달라': '뜻 란 정의', '차이': '뜻 란 정의'}


def expand(question):
    extra = [v for k, v in SYNONYMS.items() if k in question]
    return f"{question} {' '.join(extra)}" if extra else question


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--index', required=True)
    p.add_argument('--cases', default=str(ROOT / 'evaluation/cases.json'))
    p.add_argument('--out-dir', default=str(ROOT / 'evaluation/results'))
    args = p.parse_args()
    from dotenv import load_dotenv
    from langchain_openai import OpenAIEmbeddings
    load_dotenv(ROOT.parent / '.env')
    cases = read_json(args.cases)['cases']
    for c in cases:  # 잠정 평가: draft 문항도 채점 (원본 파일은 그대로)
        c['status'] = 'reviewed'
    emb = OpenAIEmbeddings(model=read_json(Path(args.index) / 'manifest.json')['embedding_model'])
    vectors = {c['id']: emb.embed_query(c['question']) for c in cases if c['category'] == 'rag'}

    def run(rewrite):
        return evaluate(cases, lambda c: search(args.index, vectors[c['id']], c['filters'],
                                                 c.get('top_k', 5), query=rewrite(c['question'])))

    before, after = run(lambda q: q), run(expand)
    out = Path(args.out_dir)
    write_json(out / 'exp01_before.json', before)
    write_json(out / 'exp01_after.json', dict(after, synonyms=SYNONYMS))
    keys = ('evaluated', 'hit_rate', 'mean_recall', 'mrr')
    print('지표        before    after')
    for k in keys[1:]:
        print(f'{k:<11} {before[k]:.3f}    {after[k]:.3f}')
    b = {r['id']: r for r in before['results'] if r['status'] == 'evaluated'}
    for r in after['results']:
        if r['status'] == 'evaluated' and (r['hit'], r['recall']) != (b[r['id']]['hit'], b[r['id']]['recall']):
            print(r['id'], f"recall {b[r['id']]['recall']:.2f} -> {r['recall']:.2f}",
                  'HIT' if r['hit'] else 'MISS')


if __name__ == '__main__':
    main()
