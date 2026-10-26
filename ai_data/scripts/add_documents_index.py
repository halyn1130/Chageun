"""기존 인덱스에 registry의 새 문서만 청크로 추가한 새 버전 인덱스를 만든다.

용도: 설명서 그림 설명 PDF(*-figures)처럼 문서가 늘었을 때, 전체를 다시 임베딩하지 않고
새 문서의 청크만 임베딩해 붙인다.

- 기존 청크·벡터·청크 ID는 그대로(평가셋이 가리킴), 새 문서 청크만 임베딩한다.
- 원본 인덱스는 수정하지 않는다. 이미 들어 있는 doc_id는 거부한다.

실행 (ai_data 폴더, OpenAI 키 필요):
  python scripts/add_documents_index.py --base data/indexes/v13c-headings \
      --doc-ids kia-k5-dl3-2026-figures hyundai-avante-cn7-2026-figures --dry-run
  python scripts/add_documents_index.py --base data/indexes/v13c-headings \
      --doc-ids kia-k5-dl3-2026-figures hyundai-avante-cn7-2026-figures --out data/indexes/v14-figures
"""
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from chageun_ai.core import (chunk_appendix_pages, chunk_cited_pages, chunk_law_pages,  # noqa: E402
                             chunk_manual_pages, digest, load_chunks, read_json, validate_document, write_json)


def chunk_document(doc, registry_dir):
    """The same chunker choice as core.ingest()."""
    from pypdf import PdfReader
    validate_document(doc)
    path = (registry_dir / doc['file']).resolve()
    content = path.read_bytes()
    pages = [p.extract_text() or '' for p in PdfReader(path).pages]
    chunker = chunk_manual_pages
    if doc['kind'] == 'law':
        chunker = chunk_appendix_pages if '[별표' in doc['title'] else chunk_law_pages
    if doc.get('chunking') == 'page':
        chunker = chunk_cited_pages
    rows, empty = chunker(doc, pages, digest(content))
    if not rows:
        raise SystemExit(f"{doc['doc_id']}: no extracted text")
    return rows, empty


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--base', required=True)
    p.add_argument('--registry', default='data/registry.json')
    p.add_argument('--doc-ids', nargs='+', required=True)
    p.add_argument('--out')
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()
    base, registry_path = Path(args.base), Path(args.registry).resolve()
    manifest = read_json(base / 'manifest.json')
    if digest((base / 'chunks.jsonl').read_bytes()) != manifest['chunks_sha256']:
        raise SystemExit('base index checksum mismatch')
    chunks = load_chunks(base / 'chunks.jsonl')
    present = {c['metadata'].get('doc_id') for c in chunks}
    docs = {d['doc_id']: d for d in read_json(registry_path)['documents']}
    added = []
    for doc_id in args.doc_ids:
        if doc_id not in docs:
            raise SystemExit(f'{doc_id}: not in registry')
        if doc_id in present:
            raise SystemExit(f'{doc_id}: already in base index')
        rows, empty = chunk_document(docs[doc_id], registry_path.parent)
        print(f'{doc_id}: 청크 {len(rows)}개, 빈 페이지 {empty}')
        added += rows
    ids = {c['chunk_id'] for c in chunks}
    if any(c['chunk_id'] in ids for c in added):
        raise SystemExit('chunk_id collision with base index')
    if args.dry_run:
        for c in added[:3]:
            print(' +', c['text'].split('\n')[0][:80])
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
    new = np.asarray(OpenAIEmbeddings(model=manifest['embedding_model']).embed_documents(
        [c['text'] for c in added]), dtype='float32')
    if new.shape != (len(added), index.d) or not np.isfinite(new).all():
        raise SystemExit('invalid embedding matrix')
    faiss.normalize_L2(new)
    merged = faiss.IndexFlatIP(index.d)
    merged.add(np.vstack([vectors, new]))
    out.mkdir(parents=True)
    all_chunks = chunks + added
    (out / 'chunks.jsonl').write_text(''.join(json.dumps(c, ensure_ascii=False) + '\n' for c in all_chunks),
                                      encoding='utf-8')
    faiss.write_index(merged, str(out / 'index.faiss'))
    write_json(out / 'manifest.json', dict(manifest, count=len(all_chunks),
                                           chunks_sha256=digest((out / 'chunks.jsonl').read_bytes()),
                                           index_sha256=digest((out / 'index.faiss').read_bytes())))
    print(f'built {out}: 기존 {len(chunks)}개 재사용 + 새 청크 {len(added)}개 임베딩')


if __name__ == '__main__':
    main()
