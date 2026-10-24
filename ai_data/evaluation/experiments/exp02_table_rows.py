"""실험 02: 정기 점검 주기표를 '항목(행) 단위' 보조 청크로 추가 색인 (실험 01 동의어 확장 위에 1개만 추가)

가설: 정기 점검표 청크는 1,000자 안팎의 표 하나에 항목 수십 개가 섞여 있어,
     "엔진오일 교환 주기" 같은 질문과 점수가 희석된다 (CG-15 실패, CG-10 4위).
변경: 기존 청크·임베딩은 그대로 두고, 점검표 청크(K5 '정기 점검 > 정기 점검', 아반떼 '통상/가혹 조건')에서
     항목 한 줄씩 떼어 낸 보조 청크(content_role=table_row, parent_chunk_id=원래 청크)를 추가한다.
     검색은 보조 청크로 하되 결과는 원래 표 청크로 돌려준다(small-to-big). 같은 표의 보조 청크가
     여러 개 걸려도 한 자리만 차지하도록 원래 청크 단위로 묶은 뒤 기존과 같은 하이브리드 순위를 매긴다.

1) 인덱스 만들기 (보조 청크만 새로 임베딩, 원본 v13b는 수정하지 않음)
   python evaluation/experiments/exp02_table_rows.py build \
       --base data/indexes/v13b-the-new-avante --out data/indexes/v14-table-rows
2) 평가 (baseline / 실험01 / 실험02를 같은 임베딩으로 비교)
   python evaluation/experiments/exp02_table_rows.py eval \
       --base data/indexes/v13b-the-new-avante --index data/indexes/v14-table-rows
"""
import argparse, hashlib, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(Path(__file__).resolve().parent))
from chageun_ai.core import (load_chunks, bm25_scores, evaluate, read_json, write_json, digest,  # noqa: E402
                             SCHEMA_VERSION)
from exp01_query_synonyms import expand  # noqa: E402

MARK = re.compile(r'[○●]|\d[\d,]*\s*km|\d+\s*개월|무점검')
SKIP = re.compile(r'^([●○]\s*:|주행\s*거리|점검\s*항목|점검$|정기 점검$|일일|[✽※]|\*\d|[\d만\s]+$|알아두기)')
SUB = re.compile(r'^(스마트스트림|Smartstream|\d\.\d\s*(LPI|T-GDi))')
SECTIONS = ('정기 점검 > 정기 점검', '정기 점검 > 통상 조건', '정기 점검 > 가혹 조건')


def is_table(c):
    m = c['metadata']
    return m.get('kind') == 'manual' and (m.get('section') or '').startswith(SECTIONS)


def rows(c, cond):
    """표 청크를 항목 한 줄씩으로 나눈다. cond는 청크를 넘어 이어지는 '통상/가혹 조건' 상태."""
    lines = c['text'].split('\n'); head = lines[0].replace(' (계속)', '')
    out, buf, last_item = [], [], ''
    for line in lines[1:]:
        s = line.strip()
        hdr = re.fullmatch(r'[^가-힣]*(통상|가혹) 조건', s)  # 표 제목 줄만 (본문 속 '가혹 조건의…'은 제외)
        if hdr: cond[0] = f'{hdr.group(1)} 조건'
        if not s or SKIP.match(s):
            buf = []; continue
        if SUB.match(s) and last_item and not buf:
            body = f'{last_item} {s}'
        elif MARK.search(s):
            body = ' '.join(buf + [s])
            last_item = ' '.join(buf) or re.split(r'\s[○●\-]|\s(?:스마트스트림|Smartstream)|\s매\s', s)[0]
        else:
            buf = (buf + [s])[-3:] if len(s) <= 40 else []
            continue
        buf = []
        if re.search(r'[가-힣A-Za-z]', body):
            tag = '' if cond[0] in head else f' [{cond[0]}]'
            out.append(f'{head}{tag} (점검 주기표 항목)\n{body}')
    return out


def children(chunks):
    res, cond, doc = [], ['통상 조건'], None
    for c in chunks:
        if not is_table(c):
            continue
        if c['metadata']['doc_id'] != doc:
            doc, cond = c['metadata']['doc_id'], ['통상 조건']
        for t in dict.fromkeys(rows(c, cond)):
            res.append({'schema_version': SCHEMA_VERSION,
                        'chunk_id': hashlib.sha256((c['chunk_id'] + t).encode()).hexdigest()[:24],
                        'text': t,
                        'metadata': dict(c['metadata'], parent_chunk_id=c['chunk_id'], content_role='table_row')})
    return res


def build(base, out, embed_documents):
    import faiss, json, numpy as np
    base, out = Path(base), Path(out)
    if out.exists():
        raise FileExistsError(f'{out} exists; choose a new version directory')
    manifest = read_json(base / 'manifest.json')
    if digest((base / 'chunks.jsonl').read_bytes()) != manifest['chunks_sha256']:
        raise ValueError('base index checksum mismatch')
    chunks = load_chunks(base / 'chunks.jsonl')
    index = faiss.read_index(str(base / 'index.faiss'))
    kids = children(chunks)
    new = np.asarray(embed_documents([k['text'] for k in kids]), dtype='float32')
    faiss.normalize_L2(new)
    old = np.asarray([index.reconstruct(i) for i in range(index.ntotal)], dtype='float32')  # 기존 임베딩 재사용
    merged = faiss.IndexFlatIP(index.d); merged.add(np.vstack([old, new]))
    out.mkdir(parents=True)
    (out / 'chunks.jsonl').write_text(''.join(json.dumps(c, ensure_ascii=False) + '\n' for c in chunks + kids),
                                     encoding='utf-8')
    faiss.write_index(merged, str(out / 'index.faiss'))
    write_json(out / 'manifest.json', dict(manifest, count=len(chunks) + len(kids),
               chunks_sha256=digest((out / 'chunks.jsonl').read_bytes()),
               index_sha256=digest((out / 'index.faiss').read_bytes()),
               note=f'{base.name} + 정기 점검표 항목 보조 청크 {len(kids)}개 (exp02)'))
    return len(chunks), len(kids)


def grouped_search(index_dir, vector, filters, top_k=5, query=None, rrf_k=60, keep_each=2, cache={}):
    """core.search와 같은 하이브리드(RRF + 각 순위 상위 keep_each 보존)를 '원래 청크' 단위로 수행.
    보조 청크가 없는 인덱스에서는 core.search와 결과가 같다."""
    import faiss, numpy as np
    if index_dir not in cache:
        chunks = load_chunks(Path(index_dir) / 'chunks.jsonl')
        cache[index_dir] = (chunks, faiss.read_index(str(Path(index_dir) / 'index.faiss')),
                            {c['chunk_id']: c for c in chunks})
    chunks, index, by_id = cache[index_dir]
    cand = [i for i, c in enumerate(chunks) if all(c['metadata'].get(k) == v for k, v in filters.items())]
    group = [chunks[i]['metadata'].get('parent_chunk_id') or chunks[i]['chunk_id'] for i in cand]
    q = np.asarray([vector], dtype='float32'); faiss.normalize_L2(q)
    sub = faiss.IndexFlatIP(index.d)
    sub.add(np.asarray([index.reconstruct(i) for i in cand], dtype='float32'))
    _, dense = sub.search(q, len(cand))
    kw = bm25_scores(query, [chunks[i]['text'] for i in cand])
    # 각 순위에서 원래 청크(그룹)가 처음 등장한 순서만 남긴다
    dense_g = list(dict.fromkeys(group[int(p)] for p in dense[0]))
    kw_g = list(dict.fromkeys(group[p] for p in sorted(range(len(cand)), key=lambda p: -kw[p]) if kw[p] > 0))
    fused = {}
    for r, g in enumerate(dense_g): fused[g] = fused.get(g, 0) + 1 / (rrf_k + r + 1)
    for r, g in enumerate(kw_g): fused[g] = fused.get(g, 0) + 1 / (rrf_k + r + 1)
    kept = list(dict.fromkeys(dense_g[:keep_each] + kw_g[:keep_each]))[:top_k]
    rest = [g for g in sorted(fused, key=lambda g: -fused[g]) if g not in kept]
    best = sorted(kept + rest[:top_k - len(kept)], key=lambda g: -fused[g])
    return [{'chunk': by_id[g], 'score': fused[g]} for g in best]


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd', required=True)
    b = sub.add_parser('build'); b.add_argument('--base', required=True); b.add_argument('--out', required=True)
    e = sub.add_parser('eval'); e.add_argument('--base', required=True); e.add_argument('--index', required=True)
    e.add_argument('--cases', default=str(ROOT / 'evaluation/cases.json'))
    e.add_argument('--out-dir', default=str(ROOT / 'evaluation/results'))
    d = sub.add_parser('preview'); d.add_argument('--base', required=True)
    args = p.parse_args()
    if args.cmd == 'preview':  # OpenAI 없이 보조 청크만 확인
        for k in children(load_chunks(Path(args.base) / 'chunks.jsonl')):
            print(k['metadata']['model'], '|', k['text'].replace('\n', ' | '))
        return
    from dotenv import load_dotenv
    from langchain_openai import OpenAIEmbeddings
    load_dotenv(ROOT.parent / '.env')
    if args.cmd == 'build':
        model = read_json(Path(args.base) / 'manifest.json')['embedding_model']
        n, k = build(args.base, args.out, OpenAIEmbeddings(model=model).embed_documents)
        print(f'built {args.out}: 기존 {n} + 보조 {k} = {n + k} chunks')
        return
    cases = read_json(args.cases)['cases']
    for c in cases:  # 잠정 평가: draft 문항도 채점 (원본 파일은 그대로)
        c['status'] = 'reviewed'
    emb = OpenAIEmbeddings(model=read_json(Path(args.base) / 'manifest.json')['embedding_model'])
    vec = {c['id']: emb.embed_query(c['question']) for c in cases if c['category'] == 'rag'}

    def run(index, rewrite):
        return evaluate(cases, lambda c: grouped_search(index, vec[c['id']], c['filters'], c.get('top_k', 5),
                                                         query=rewrite(c['question'])))
    runs = {'baseline': run(args.base, lambda q: q), 'exp01': run(args.base, expand), 'exp02': run(args.index, expand)}
    out = Path(args.out_dir)
    for name, r in runs.items():
        write_json(out / f'exp02_{name}.json', dict(r, index=args.index if name == 'exp02' else args.base))
    print(f"{'지표':<12}" + ''.join(f'{n:>10}' for n in runs))
    for k in ('hit_rate', 'mean_recall', 'mrr'):
        print(f'{k:<12}' + ''.join(f'{r[k]:>10.3f}' for r in runs.values()))
    rr = {n: {x['id']: x for x in r['results'] if x['status'] == 'evaluated'} for n, r in runs.items()}
    print('\n문항     첫 정답 순위(baseline -> exp01 -> exp02)')
    for cid in rr['baseline']:
        ranks = ['-' if rr[n][cid]['reciprocal_rank'] == 0 else str(round(1 / rr[n][cid]['reciprocal_rank']))
                 for n in runs]
        if len(set(ranks)) > 1:
            print(f'{cid:<8} ' + ' -> '.join(ranks))


if __name__ == '__main__':
    main()
