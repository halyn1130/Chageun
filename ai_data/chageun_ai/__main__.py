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
    for name in ('search', 'answer', 'evaluate', 'evaluate-answers', 'ask'):
        q = commands.add_parser(name)
        q.add_argument('--index', required=True)
        if name in ('evaluate', 'evaluate-answers'):
            q.add_argument('--cases', default='evaluation/cases.json')
            q.add_argument('--out', default=f"evaluation/results/{'answers' if name == 'evaluate-answers' else 'latest'}.json")
            if name == 'evaluate-answers':
                q.add_argument('--runs', type=int, default=1, help='repeat each case to measure stability')
                q.add_argument('--include-drafts', action='store_true', help='score unreviewed cases (provisional)')
                q.add_argument('--llm-model', default='gpt-4o-mini')
        elif name == 'ask':
            q.add_argument('question')
            q.add_argument('--vehicle', help='vehicle object as the api-server sends it, e.g. {"id":3,"manufacturer":"기아",...}')
            q.add_argument('--conversation-id')
            q.add_argument('--top-k', type=int, default=8)
        else:
            q.add_argument('question')
            q.add_argument('--filters', required=True, help='JSON object, e.g. {"kind":"law"}')
            q.add_argument('--top-k', type=int, default=5)
        if name in ('answer', 'ask'):
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
                args.index, embedding.embed_query(case['question']), case['filters'], case.get('top_k', 5),
                query=case['question']))
            write_json(args.out, result)
        elif args.command == 'evaluate-answers':
            from .evaluation import evaluate_pipeline
            from .server import Engine
            engine = Engine(args.index, args.llm_model)

            retrieve = engine.retrieve

            def ask(request):
                seen = []

                def traced(query, filters):
                    hits = retrieve(query, filters)
                    seen.extend(h['chunk']['chunk_id'] for h in hits)
                    return hits
                engine.retrieve = traced
                return engine.ask(request), seen
            report = evaluate_pipeline(read_json(args.cases)['cases'], ask, args.runs, args.include_drafts)
            write_json(args.out, dict(report, index=args.index, llm_model=args.llm_model))
            result = {k: v for k, v in report.items() if k != 'results'}
        elif args.command == 'ask':
            from langchain_openai import ChatOpenAI
            from .agent import rag_query
            llm = ChatOpenAI(model=args.llm_model, temperature=0)
            json_llm = llm.bind(response_format={'type': 'json_object'})

            def choose(system, question, tools):
                calls = llm.bind_tools(tools, tool_choice='required').invoke([('system', system), ('human', question)]).tool_calls
                return (calls[0]['name'], calls[0]['args']) if calls else None
            request = {'request_id': 'cli', 'question': args.question, 'conversation_id': args.conversation_id,
                       'vehicle': json.loads(args.vehicle) if args.vehicle else None,
                       'maintenance': {'lookup_status': 'not_requested', 'items': [], 'records': []},
                       'history': [], 'location': None}
            result = rag_query(
                request, choose,
                lambda query, filters: search(args.index, embedding.embed_query(query), filters, args.top_k, query=query),
                lambda system, user: json_llm.invoke([('system', system), ('human', user)]).content)
        else:
            if not args.question.strip():
                p.error('question cannot be empty')
            hits = search(args.index, embedding.embed_query(args.question), json.loads(args.filters), args.top_k,
                          query=args.question)
            result = hits
            if args.command == 'answer':
                from langchain_openai import ChatOpenAI
                llm = ChatOpenAI(model=args.llm_model, temperature=0, model_kwargs={'response_format': {'type': 'json_object'}})
                result = answer_from_hits(args.question, hits, lambda system, user: llm.invoke(
                    [('system', system), ('human', user)]).content)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
