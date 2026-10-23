import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  oilSchedule,
  warningForFlow,
  warningAnswer,
} from '../src/vehicleGuide.js'

const car = {
  manufacturer: '기아',
  model: 'K5',
  model_year: '2024',
  powertrain: '가솔린 1.6T',
  mileage_km: 36200,
}
const record = {
  item: 'engine_oil',
  performed_at: '2024-01-10',
  mileage_km: 35000,
}

test('oil interval applies only to the verified exact model and powertrain', () => {
  for (const change of [
    { model: '아반떼' },
    { model_year: 2025 },
    { powertrain: '가솔린 2.0' },
    { manufacturer: '현대' },
    { powertrain: '하이브리드 1.6T' },
  ]) {
    assert.equal(
      oilSchedule({ ...car, ...change }, [record]).status,
      'unsupported',
    )
  }
})
test('calendar due is reached even when mileage remains', () => {
  const value = oilSchedule(car, [record], 'normal', '2025-01-10')
  assert.equal(value.status, 'due')
  assert.equal(value.nextKm, 45000)
  assert.equal(value.dateDue, true)
  assert.equal(value.mileageDue, false)
})
test('mileage can trigger first, including the exact due kilometer', () => {
  const value = oilSchedule(
    { ...car, mileage_km: 45000 },
    [record],
    'normal',
    '2024-06-01',
  )
  assert.equal(value.status, 'due')
  assert.equal(value.dateDue, false)
  assert.equal(value.mileageDue, true)
})
test('severe conditions use 5,000 km and six months; month end is clamped', () => {
  const value = oilSchedule(
    car,
    [{ ...record, performed_at: '2023-08-31' }],
    'severe',
    '2024-02-28',
  )
  assert.equal(value.nextKm, 40000)
  assert.equal(value.nextDate, '2024-02-29')
  assert.equal(value.status, 'upcoming')
})
test('newest dated oil record is used without mutating records or using other items', () => {
  const records = [
    record,
    { ...record, item: 'tire', performed_at: '2024-06-01' },
    { ...record, performed_at: '2024-05-01', mileage_km: 36000 },
  ]
  const value = oilSchedule(car, records, 'normal', '2024-06-01')
  assert.equal(value.nextKm, 46000)
  assert.equal(value.nextDate, '2025-05-01')
  assert.equal(records[0], record)
})
test('invalid dates, future records and odometer inconsistencies cannot produce a due claim', () => {
  assert.equal(oilSchedule(car, [], 'normal', '2024-06-01').status, 'no_record')
  for (const change of [
    { performed_at: '2024-02-31' },
    { performed_at: '2025-01-01' },
    { mileage_km: 40000 },
    { mileage_km: -1 },
  ]) {
    assert.equal(
      oilSchedule(car, [{ ...record, ...change }], 'normal', '2024-06-01')
        .status,
      'invalid_record',
    )
  }
})
test('ambiguous symbol or contradictory color does not become a confirmed warning', () => {
  assert.equal(
    warningForFlow({
      intent: 'warning',
      original: '노란 느낌표 불이 켜졌어',
      details: {},
    }),
    null,
  )
  assert.equal(
    warningForFlow({
      intent: 'warning',
      original: '빨간 엔진 모양 불',
      details: { color: '빨간색' },
    }),
    null,
  )
  assert.equal(
    warningForFlow({
      intent: 'maintenance',
      original: '엔진오일 언제 갈아',
      details: {},
    }),
    null,
  )
  assert.equal(
    warningForFlow({
      intent: 'warning',
      original: '노란 엔진 모양 불',
      details: { color: '노란색' },
    }),
    'engine',
  )
  assert.equal(
    warningAnswer('oil').sources[0].url.includes('ownersmanual.kia.com'),
    true,
  )
})
