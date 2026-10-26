"""RAG 서버 로그의 `usage` 줄을 모아 질문당 원가·토큰·응답 시간을 요약한다.

배경: 내비게이션 플러그인처럼 질문 수가 많은 구조에서는 질문당 몇 원 차이가 월 원가를 좌우한다.
모델·청크 수·준비된 답변 비율을 바꿀 때 추정이 아니라 실제 요청으로 비교하기 위해 쓴다.
비용은 server.PRICES(또는 RAG_PRICES)의 단가로 계산한 추정치이며 실제 청구액과 다를 수 있다.

실행 (저장소 루트):
  docker compose logs rag --no-log-prefix | python ai_data/scripts/usage_report.py
  docker compose logs rag --no-log-prefix --since 1h | python ai_data/scripts/usage_report.py --krw 1400
"""
import argparse, json, statistics, sys
from collections import Counter, defaultdict


def percentile(values, p):
    values = sorted(values)
    return values[min(len(values) - 1, int(len(values) * p))] if values else 0


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--krw', type=float, default=0, help='원/달러 환율. 주면 원화로도 표시한다')
    args = p.parse_args()
    records = []
    for line in sys.stdin:
        _, found, payload = line.partition('usage {')
        if found:
            records.append(json.loads('{' + payload))
    if not records:
        sys.exit('usage 로그가 없어요. 서버가 이 기능이 들어간 버전인지, 질문을 보낸 뒤인지 확인해 주세요.')

    priced = [r['cost_usd'] for r in records if r['cost_usd'] is not None]
    money = lambda usd: f'${usd:.4f}' + (f' ({usd * args.krw:,.1f}원)' if args.krw else '')
    ms = [r['total_ms'] for r in records]
    print(f'요청 {len(records)}건 · 상태 ' + ', '.join(f'{k} {v}' for k, v in Counter(r['status'] for r in records).most_common()))
    print(f'응답 시간  평균 {statistics.mean(ms) / 1000:.1f}초 · 중앙값 {percentile(ms, .5) / 1000:.1f}초 · '
          f'90% {percentile(ms, .9) / 1000:.1f}초')
    if priced:
        print(f'질문당 원가  평균 {money(statistics.mean(priced))} · 최대 {money(max(priced))} · '
              f'1,000건 {money(statistics.mean(priced) * 1000)}')
    if len(priced) < len(records):
        print(f'단가가 없는 모델이 쓰인 요청 {len(records) - len(priced)}건은 원가에서 뺐어요 (RAG_PRICES로 추가).')

    steps = defaultdict(list)
    for r in records:
        for call in r['calls']:
            steps[(call['step'], call['model'])].append(call)
    print('\n단계별 (호출 1회 평균)')
    print(f'{"단계":<8}{"모델":<28}{"호출":>6}{"입력":>8}{"출력":>6}{"시간":>8}{"원가 합계":>14}')
    for (step, model), calls in sorted(steps.items(), key=lambda kv: -sum(c['cost_usd'] or 0 for c in kv[1])):
        total = sum(c['cost_usd'] or 0 for c in calls)
        print(f'{step:<8}{model or "?":<28}{len(calls):>6}{statistics.mean(c["in"] for c in calls):>8.0f}'
              f'{statistics.mean(c["out"] for c in calls):>6.0f}{statistics.mean(c["ms"] for c in calls) / 1000:>7.1f}s'
              f'{"$" + format(total, ".4f"):>14}')


if __name__ == '__main__':
    main()
