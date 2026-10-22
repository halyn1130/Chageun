import argparse
import json
import os
from pathlib import Path
from .core import ingest, build_index, search, read_json, write_json, answer_from_hits, evaluate


def main():
    p = argparse.ArgumentParser(description='차근 데이터/RAG CLI — HTTP API와 독립 실행')
    commands = p.add_subparsers(dest='command', required=True)
    i = commands.add_parser('ingest')
    i.add_argument('--registry', default='data/registry.json')
    i.add_argument('--out', default='data/processed')
    b = commands.add_parser('build')
    b.add_argument('--chunks', default='data/processed/chunks.jsonl')
    b.add_argument('--index', required=True)
    b.add_argument('--embedding-model', default='text-embedding-3-small')
    for name in ('search', 'answer', 'evaluate'):
        q = commands.add_parser(name)
        q.add_argument('--index', required=True)
        if name == 'evaluate':
            q.add_argument('--cases', default='evaluation/cases.json')
            q.add_argument('--out', default='evaluation/results/latest.json')
        else:
            q.add_argument('question')
            q.add_argument('--filters', required=True, help='JSON object, e.g. {"kind":"law"}')
            q.add_argument('--top-k', type=int, default=5)
        if name == 'answer':
            q.add_argument('--llm-model', default='gpt-4o-mini')
    args = p.parse_args()
    if args.command == 'ingest':
        result = ingest(args.registry, args.out)
    else:
        from dotenv import load_dotenv
        from langchain_openai import OpenAIEmbeddings
        load_dotenv(Path(__file__).resolve().parents[2] / '.env')
        if not os.getenv('OPENAI_API_KEY'):
            p.error('OPENAI_API_KEY required; ingest and unit tests run without a key')
        model = args.embedding_model if args.command == 'build' else read_json(Path(args.index) / 'manifest.json')['embedding_model']
        embedding = OpenAIEmbeddings(model=model)
        if args.command == 'build':
            build_index(args.chunks, args.index, embedding.embed_documents, model)
            result = {'status': 'built', 'index': args.index, 'embedding_model': model}
        elif args.command == 'evaluate':
            result = evaluate(read_json(args.cases)['cases'], lambda case: search(
                args.index, embedding.embed_query(case['question']), case['filters'], case.get('top_k', 5)))
            write_json(args.out, result)
        else:
            if not args.question.strip():
                p.error('question cannot be empty')
            hits = search(args.index, embedding.embed_query(args.question), json.loads(args.filters), args.top_k)
            result = hits
            if args.command == 'answer':
                from langchain_openai import ChatOpenAI
                llm = ChatOpenAI(model=args.llm_model, temperature=0)
                result = answer_from_hits(args.question, hits, lambda system, user: llm.invoke(
                    [('system', system), ('human', user)]).content)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
