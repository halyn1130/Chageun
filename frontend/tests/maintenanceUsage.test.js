import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { maintenanceUsage, maintenancePriorities, sortMaintenanceUsages, usageState, vehicleMaintenanceTones } from '../src/maintenanceUsage.js'
import { maintenanceCatalog } from '../src/guidance.js'
import { localBoundary } from '../src/conversation.js'
const vehicle = { manufacturer:'기아', model:'K5', model_year:'2024', powertrain:'가솔린 1.6T', mileage_km:36200 }
const oil = maintenanceCatalog.find(item => item.id === 'oil')
const records = [{ item:'engine_oil', performed_at:'2026-04-23', mileage_km:31000 }]
const options = { now:'2026-10-23' }

test('distance and elapsed time are independent; low mileage never hides overdue calendar time', () => {
  const current = maintenanceUsage(vehicle, records, oil, options)
  assert.equal(current.distance, 5200)
  assert.equal(current.distanceRatio, .52)
  assert.equal(current.months, 6)
  assert.equal(current.needsConfirmation, false)
  const old = maintenanceUsage(vehicle, [{ ...records[0], performed_at:'2024-01-10', mileage_km:35000 }], oil, options)
  assert.equal(old.distanceRatio, .12)
  assert.equal(old.timeRatio, 1)
  assert.equal(old.dateDue, true)
  assert.equal(old.needsConfirmation, true)
})
test('severe-use comparison changes both distance and time limits and clamps the graphic', () => {
  const value = maintenanceUsage(vehicle, records, oil, { ...options, condition:'severe' })
  assert.deepEqual(value.interval, { km:5000, months:6 })
  assert.equal(value.distance, 5200)
  assert.equal(value.distanceRatio, 1)
  assert.equal(value.mileageDue, true)
  assert.equal(value.dateDue, true)
})
test('missing, unavailable and inconsistent records are not shown as zero usage', () => {
  for (const value of [maintenanceUsage(vehicle, [], oil, options), maintenanceUsage(vehicle, records, oil, { ...options, error:'offline' }), maintenanceUsage(vehicle, [{...records[0], mileage_km:40000}], oil, options), maintenanceUsage(vehicle, [{...records[0], performed_at:'2027-01-01'}], oil, options)]) {
    assert.equal(value.distance, null)
    assert.equal(value.distanceRatio, null)
  }
  assert.equal(maintenanceUsage(vehicle, records, oil, {...options,error:'offline'}).status, 'unavailable')
})
test('unknown car specifications and other parts never inherit the reviewed oil interval', () => {
  const unsupported = maintenanceUsage({...vehicle,model_year:'2026'},records,oil,options)
  assert.equal(unsupported.distance, 5200)
  assert.equal(unsupported.interval,null)
  assert.equal(unsupported.distanceRatio,null)
  const tire = maintenanceCatalog.find(item=>item.id==='tire')
  const result = maintenanceUsage(vehicle,[{...records[0],item:'tire'}],tire,options)
  assert.equal(result.distance,5200)
  assert.equal(result.interval,null)
})
test('a missing odometer still permits a calendar comparison but never a mileage estimate', () => {
  const value = maintenanceUsage({...vehicle,mileage_km:null},records,oil,options)
  assert.equal(value.distance,null)
  assert.equal(value.distanceRatio,null)
  assert.equal(value.months,6)
  assert.ok(value.timeRatio > .4 && value.timeRatio < .6)
})
const fixture = JSON.parse(readFileSync(new URL('../../infra/db/demo-account-1.json', import.meta.url))).vehicles[0]
test('all ten demo parts have separate usage targets and sort by the first distance or date limit', () => {
  const values = maintenancePriorities(vehicle, fixture.records, options)
  assert.equal(values.length, 10)
  assert.ok(values.every(value => value.distanceRatio != null && value.timeRatio != null))
  assert.deepEqual(values.slice(0, 4).map(value => value.item.id), ['wiper', 'brake-pad', 'oil', 'oil-filter'])
  assert.equal(values[0].dateDue, true)
  assert.ok(values[0].distanceRatio < .9)
  assert.equal(values[1].distanceRatio, .94)
  assert.ok(values.every((value, index) => !index || values[index - 1].priorityRatio >= value.priorityRatio))
})
test('the 2026 car uses its own reviewed manual interval', () => {
  assert.equal(fixture.vehicle.model_year, '2026')
  assert.equal(fixture.vehicle.powertrain, 'G2.0')
  const values = maintenancePriorities(fixture.vehicle, fixture.records, options)
  const oilUsage = values.find(value => value.item.id === 'oil')
  assert.equal(oilUsage.distance, 9200)
  assert.deepEqual(oilUsage.interval, {km:8000, months:12})
  assert.equal(oilUsage.intervalSource, 'user_setting')
  assert.equal(values.filter(value => value.conditionBased).length, 4)
  assert.ok(values.every(value => value.source))
})
test('car colors retain the most urgent item when multiple records share one illustrated assembly', () => {
  const values = maintenancePriorities(vehicle, fixture.records, options)
  const tones = vehicleMaintenanceTones(values)
  assert.equal(tones.engine, 'urgent')
  assert.equal(tones.brakes, 'urgent')
  assert.equal(tones.coolant, 'soon')
  assert.equal(tones.wiper, 'urgent')
  assert.equal(tones.battery, 'soon')
  assert.deepEqual(vehicleMaintenanceTones([...values].reverse()), tones)
  assert.deepEqual(vehicleMaintenanceTones(maintenancePriorities(vehicle, [], options)), {})
})
test('color thresholds are explicit, and missing records are never marked comfortable', () => {
  assert.deepEqual([.69, .7, .89, .9, 1, 1.2].map(priorityRatio => usageState({ priorityRatio }).tone), ['comfortable','soon','soon','urgent','urgent','urgent'])
  assert.equal(usageState({priorityRatio:1}).label, '교환 시점')
  assert.equal(usageState(maintenanceUsage(vehicle, [], oil, options)).tone, 'unknown')
})
test('example intervals require demo records and never impersonate a reviewed oil interval on another car', () => {
  const tire = maintenanceCatalog.find(item => item.id === 'tire')
  const realRecord = [{...records[0], item:'tire'}]
  assert.equal(maintenanceUsage(vehicle, realRecord, tire, {...options,demo:true}).interval, null)
  const preview = maintenanceUsage(vehicle, fixture.records, tire, {...options,demo:true})
  assert.equal(preview.intervalSource, 'demo')
  assert.equal(maintenanceUsage({...vehicle, model:'아반떼'}, fixture.records, oil, {...options,demo:true}).interval, null)
})
test('new replacement records reset urgency while overdue amounts remain sortable beyond 100 percent', () => {
  const newRecords = [...fixture.records, {item:'wiper', performed_at:options.now, mileage_km:36200}]
  const updated = maintenancePriorities(vehicle, newRecords, options)
  const wiper = updated.find(value => value.item.id === 'wiper')
  assert.equal(wiper.priorityRatio, 0)
  assert.equal(updated[0].item.id, 'brake-pad')
  const past = maintenancePriorities({...vehicle,mileage_km:60000}, fixture.records, options)
  assert.ok(past[0].priorityRatio > 1)
  assert.equal(past[0].distanceRatio, 1)
  assert.equal(past.at(-1).item.id, 'coolant')
})
test('demo calendar intervals clamp leap-day anniversaries and tolerate a missing odometer', () => {
  const wiper = maintenanceCatalog.find(item => item.id === 'wiper')
  const value = maintenanceUsage({...vehicle,mileage_km:null}, [{item:'wiper',performed_at:'2024-02-29',mileage_km:5000,memo:'[차근 시연]'}], wiper, {demo:true,now:'2025-02-28'})
  assert.equal(value.nextDate, '2025-02-28')
  assert.equal(value.dateDue, true)
  assert.equal(value.distanceRatio, null)
  assert.equal(value.priorityRatio, 1)
})
test('removed workshop search cannot produce a location action, while maintenance advice remains available', () => {
  for (const text of ['가까운 정비소 찾아줘', '공업소 어디 있어?', '주변 카센터 추천']) {
    assert.equal(localBoundary(text).status, 'out_of_scope')
    assert.equal(localBoundary(text).action, undefined)
  }
  assert.equal(localBoundary('정비소에서 엔진오일을 갈았어'), null)
})

const k5 = {manufacturer:'기아',model:'K5',model_year:'2026',powertrain:'G2.0',mileage_km:36200}
test('2026 K5 remaining mileage and calendar use its own latest record and source', () => {
  const value = maintenanceUsage(k5,[{item:'engine_oil',performed_at:'2026-01-24',mileage_km:25000}],oil,{now:'2026-10-24'})
  assert.equal(value.remainingKm,-3200)
  assert.equal(value.nextDate,'2027-01-24')
  assert.equal(value.remainingDays,92)
  assert.equal(value.source.chunk_id,'c899db930ecd587d2911f2c1')
  const severe = maintenanceUsage(k5,[{item:'engine_oil',performed_at:'2026-01-24',mileage_km:25000}],oil,{now:'2026-10-24',condition:'severe'})
  assert.equal(severe.remainingKm,-3700)
  assert.equal(severe.needsConfirmation,true)
})
test('calendar-only and distance-only manual rules do not manufacture another deadline', () => {
  const cabin=maintenanceCatalog.find(i=>i.recordId==='cabin_filter')
  const avante={manufacturer:'현대',model:'더 뉴 아반떼',model_year:'2026',powertrain:'G1.6',mileage_km:20500}
  const value=maintenanceUsage(avante,[{item:'cabin_filter',performed_at:'2026-05-16',mileage_km:14500}],cabin,{now:'2026-10-24'})
  assert.equal(value.nextKm,null)
  assert.equal(value.remainingKm,null)
  assert.equal(value.nextDate,'2027-05-16')
  const brake=maintenanceCatalog.find(i=>i.recordId==='brake_fluid')
  const b=maintenanceUsage(k5,[{item:'brake_fluid',performed_at:'2026-04-18',mileage_km:29000}],brake,{now:'2026-10-24'})
  assert.equal(b.nextDate,null)
  assert.equal(b.remainingKm,42800)
  assert.equal(maintenanceUsage(k5,[{item:'cabin_filter',performed_at:'2026-05-16',mileage_km:14500}],cabin,{now:'2026-10-24',condition:'severe'}).interval,null)
})

test('registered Avante alias receives engine oil and filter manual intervals', () => {
 const car={manufacturer:'현대',model:'디 올 뉴 아반떼',model_year:'2026',powertrain:'G1.6',mileage_km:20500}
 for(const id of ['engine_oil','oil_filter']) {
  const part=maintenanceCatalog.find(i=>i.recordId===id)
  const value=maintenanceUsage(car,[{item:id,performed_at:'2026-09-12',mileage_km:18500}],part,{now:'2026-10-24'})
  assert.deepEqual(value.interval,{km:15000,months:12})
  assert.equal(value.remainingKm,13000)
  assert.equal(value.intervalSource,'manual')
 }
})


test('condition-based items keep history without inventing a replacement deadline', () => {
 for (const car of [k5, {manufacturer:'현대',model:'더 뉴 아반떼',model_year:'2026',powertrain:'G1.6',mileage_km:36200}]) {
  for (const id of ['tire','brake_pad','wiper','battery']) {
   const part=maintenanceCatalog.find(i=>i.recordId===id)
   const value=maintenanceUsage(car,[{item:id,performed_at:'2026-01-01',mileage_km:20000,memo:'[차근 시연]'}],part,{now:'2026-10-25',demo:true})
   assert.equal(value.interval,null)
   assert.equal(value.priorityRatio,null)
   assert.equal(value.distance,16200)
   assert.equal(value.nextDate,null)
   assert.equal(usageState(value).label,'상태 점검')
   assert.ok(value.ruleNote && value.source)
  }
  const air=maintenanceCatalog.find(i=>i.recordId==='air_filter')
  const rec=[{item:'air_filter',performed_at:'2026-01-01',mileage_km:10000}]
  assert.equal(maintenanceUsage(car,rec,air,{now:'2026-10-25'}).nextKm,50000)
  assert.equal(maintenanceUsage(car,rec,air,{now:'2026-10-25',condition:'severe'}).interval,null)
  const coolant=maintenanceCatalog.find(i=>i.recordId==='coolant')
  assert.equal(maintenanceUsage(car,[],coolant,{now:'2026-10-25'}).nextDate,undefined)
  assert.match(maintenanceUsage(car,[],coolant,{now:'2026-10-25'}).ruleNote,/최초 교환은 200,000km/)
 }
})

test('care list offers stable catalog order and explicit urgency order without changing the source', () => {
 const values = maintenanceCatalog.map((item,index)=>({item,priorityRatio:index===3?1.1:index===2?null:.2})).reverse()
 const snapshot=values.map(v=>v.item.id)
 assert.deepEqual(sortMaintenanceUsages(values).map(v=>v.item.id),maintenanceCatalog.map(i=>i.id))
 assert.equal(sortMaintenanceUsages(values,'urgent')[0].item.id,maintenanceCatalog[3].id)
 assert.equal(sortMaintenanceUsages(values,'urgent').at(-1).item.id,maintenanceCatalog[2].id)
 assert.deepEqual(values.map(v=>v.item.id),snapshot)
})
