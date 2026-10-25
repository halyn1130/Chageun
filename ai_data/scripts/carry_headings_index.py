"""기존 인덱스에서 '청크 끝에 홀로 남은 제목'을 다음 청크 앞으로 옮긴 새 인덱스를 만든다.

배경: 청크를 1,000자 단위로 자르다 "엔진 경고등" 같은 제목이 앞 청크 끝에 남고, 설명은 다음 청크로
넘어갔다. 그러면 검증 LLM이 그 설명이 어느 경고등 것인지 알 수 없어 답변을 탈락시킨다
(2026-10-25 진단: K5 엔진 경고등 질문 실패). chunk_manual_pages는 이제 제목을 본문과 함께 두지만,
원문 PDF를 다시 처리하지 않고 기존 인덱스를 고치기 위해 이 스크립트를 쓴다.

- 청크 ID는 그대로(평가셋이 가리킴), 바뀐 청크만 새로 임베딩하고 나머지 벡터는 재사용한다.
- 원본 인덱스는 수정하지 않는다.

실행 (ai_data 폴더, OpenAI 키 필요):
  python scripts/carry_headings_index.py --base data/indexes/v13b-the-new-avante --out data/indexes/v13c-headings
  python scripts/carry_headings_index.py --base data/indexes/v13b-the-new-avante --dry-run   # 바뀔 청크만 확인
"""
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from chageun_ai.core import carry_dangling_headings, digest, load_chunks, read_json, write_json  # noqa: E402


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--base', required=True)
    p.add_argument('--out')
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()
    base = Path(args.base)
    manifest = read_json(base / 'manifest.json')
    if digest((base / 'chunks.jsonl').read_bytes()) != manifest['chunks_sha256']:
        raise SystemExit('base index checksum mismatch')
    chunks = load_chunks(base / 'chunks.jsonl')
    fixed, changed = carry_dangling_headings(chunks)
    print(f'바뀐 청크 {len(changed)}개 / 전체 {len(chunks)}개')
    if args.dry_run:
        for c in fixed:
            if c['chunk_id'] in changed and c['text'].partition('\n')[0].endswith(' (계속)'):
                print(' +', c['metadata'].get('model'), '|', c['text'].split('\n')[1][:40])
        return
    if not args.out:
        raise SystemExit('--out required')
    out = Path(args.out)
    if out.exists():
        raise SystemExit(f'{out} exists; choose a new version directory')
    import faiss, numpy as np
    from dotenv import load_dotenv
    from langchain_openai import OpenAIEmbeddings
    load_dotenv(ROOT.parent / '.env')
    index = faiss.read_index(str(base / 'index.faiss'))
    vectors = np.asarray([index.reconstruct(i) for i in range(index.ntotal)], dtype='float32')
    rows = [i for i, c in enumerate(fixed) if c['chunk_id'] in set(changed)]
    new = np.asarray(OpenAIEmbeddings(model=manifest['embedding_model']).embed_documents(
        [fixed[i]['text'] for i in rows]), dtype='float32')
    faiss.normalize_L2(new)
    vectors[rows] = new
    merged = faiss.IndexFlatIP(index.d)
    merged.add(vectors)
    out.mkdir(parents=True)
    (out / 'chunks.jsonl').write_text(''.join(json.dumps(c, ensure_ascii=False) + '\n' for c in fixed), encoding='utf-8')
    faiss.write_index(merged, str(out / 'index.faiss'))
    write_json(out / 'manifest.json', dict(manifest, chunks_sha256=digest((out / 'chunks.jsonl').read_bytes()),
                                           index_sha256=digest((out / 'index.faiss').read_bytes())))
    print(f'built {out}: 재임베딩 {len(rows)}개, 나머지 재사용')


if __name__ == '__main__':
    main()
