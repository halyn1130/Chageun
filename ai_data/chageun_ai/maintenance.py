"""Deterministic scheduling from reviewed manual rows and server-owned records."""
import calendar
import json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

RULES = json.loads(Path(__file__).with_name('maintenance_rules.json').read_text())
LABELS = {'engine_oil': '엔진오일', 'oil_filter': '엔진오일 필터', 'cabin_filter': '에어컨 필터', 'brake_fluid': '브레이크액', 'coolant': '냉각수', 'air_filter': '엔진 에어필터', 'tire': '타이어', 'brake_pad': '브레이크 패드', 'wiper': '와이퍼', 'battery': '배터리'}

def add_months(day, months):
    year, month = divmod(day.year * 12 + day.month - 1 + months, 12)
    return date(year, month + 1, min(day.day, calendar.monthrange(year, month + 1)[1]))

def maintenance_answer(vehicle, maintenance, item, condition='normal', today=None):
    today = today or datetime.now(ZoneInfo('Asia/Seoul')).date()
    model = '더 뉴 아반떼' if vehicle.get('model') == '디 올 뉴 아반떼' else vehicle.get('model')
    car = next((r for r in RULES if r['manufacturer'] == vehicle.get('manufacturer') and r['model'] == model and r['model_year'] == str(vehicle.get('model_year')) and r['powertrain'] == vehicle.get('powertrain')), None)
    rule = (car or {}).get('items', {}).get(item, {}).get(condition)
    if not rule:
        return None
    source = {k: rule['source'][k] for k in ('title', 'page', 'url')}
    label = LABELS[item]
    prefix = f"{'가혹' if condition == 'severe' else '일반'} 운행 조건 기준이에요. "
    if not rule['km'] and not rule['months']:
        return prefix + f'{label}는 고정 교환일을 계산하지 않아요. ' + rule.get('note', '상태를 점검한 뒤 필요시 교환하세요.'), [source] + ([{k: rule['age_source'][k] for k in ('title', 'page', 'url')}] if rule.get('age_source') else [])
    limits = [f"{rule['km']:,}km"] if rule['km'] else []
    if rule['months']: limits.append(f"{rule['months']}개월")
    basis = "사용자 설정" if rule.get("basis") == "user_setting" else "매뉴얼"
    prefix += f"{basis}의 {label} 교환 기준은 {' 또는 '.join(limits)}이에요. "
    if rule.get('basis') == 'user_setting': prefix += f"매뉴얼 일반 기준 {rule['manual_km']:,}km보다 짧게 설정한 값이에요. "
    if item == 'coolant': prefix += '최초 교환은 200,000km 또는 10년이며, 이 계산은 최초 교환 이후의 반복 주기 기준이에요. '
    if maintenance.get('lookup_status') not in ('ok', 'empty'):
        return prefix + '정비 기록을 불러오지 못해 개인 교환 시점은 계산하지 않았어요.', [source]
    rows = [row for row in maintenance.get('records', []) if row.get('item') == item]
    if not rows:
        return prefix + '마지막 교환 날짜와 당시 주행거리를 등록해 주세요.', [source]
    last = max(rows, key=lambda row: str(row.get('performed_at', '')))
    try:
        day = date.fromisoformat(last['performed_at'])
        km = last['mileage_km']; current = vehicle.get('mileage_km')
        if day > today or type(km) is not int or km < 0 or (current is not None and (type(current) is not int or current < km)):
            raise ValueError()
    except (ValueError, KeyError, TypeError):
        return prefix + '기록의 날짜와 주행거리를 확인해 주세요. 현재 기록으로는 계산할 수 없어요.', [source]
    remaining, targets = [], []
    due = False
    if rule['months']:
        target = add_months(day, rule['months']); days = (target - today).days
        targets.append(str(target))
        months = (target.year - today.year) * 12 + target.month - today.month
        time = f'{months}개월' if days > 0 and add_months(today, months) == target else f'{abs(days)}일'
        remaining.append(f'{time} 남음' if days > 0 else '오늘 날짜 기준 도달' if days == 0 else f'{abs(days)}일 초과')
        due |= days <= 0
    if rule['km']:
        target = km + rule['km']; targets.append(f'{target:,}km')
        if current is None: remaining.append('현재 주행거리 입력 필요')
        else:
            left = target - current; due |= left <= 0
            remaining.append(f'{left:,}km 남음' if left > 0 else '거리 기준 도달' if left == 0 else f'{-left:,}km 초과')
    answer = prefix + f"마지막 교환은 {day}, {km:,}km예요. " + ' · '.join(remaining) + '. '
    answer += f"다음 기준은 {' 또는 '.join(targets)}이며 먼저 도달할 때 확인해 주세요. "
    if due: answer += '기준에 도달했거나 지났으니 이후 교환 여부와 정비 일정을 확인해 주세요. '
    answer += '등록된 기록 기준이며, 일반 조건 안내라면 짧은 거리·잦은 정체 등 가혹 조건 여부도 확인해 주세요.'
    return answer, [source]
