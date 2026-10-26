import test from 'node:test'
import assert from 'node:assert/strict'
import { createRenderer, h } from 'vue'
import { useChageun } from '../src/composables/useChageun.js'

async function setup(run) {
  const previous = Object.fromEntries(['window', 'localStorage', 'fetch'].map(key => [key, Object.getOwnPropertyDescriptor(globalThis, key)]))
  const requests = []
  let patchResponse = null
  globalThis.localStorage = { getItem: () => null, removeItem() {}, setItem() {} }
  globalThis.window = { location: { origin: 'http://localhost' }, addEventListener() {}, removeEventListener() {} }
  globalThis.fetch = async (url, options = {}) => {
    if (['POST', 'PATCH'].includes(options.method) && options.body) {
      const body = JSON.parse(options.body)
      requests.push({ path: new URL(url).pathname, body })
      if (options.method === 'PATCH' && patchResponse) return patchResponse()
      return new Response(JSON.stringify({ id: requests.length, ...body }))
    }
    return new Response(JSON.stringify([]))
  }
  const renderer = createRenderer({
    createElement: () => ({}), createText: () => ({}), createComment: () => ({}),
    setText() {}, setElementText() {}, patchProp() {}, insert() {}, remove() {},
    parentNode: () => null, nextSibling: () => null,
  })
  let state
  const app = renderer.createApp({ setup() { state = useChageun(); return () => h('div') } })
  try {
    app.mount({})
    await new Promise(resolve => setImmediate(resolve))
    state.vehicles.value = [{ id: 2, mileage_km: 36200 }, { id: 3, mileage_km: 12000 }]
    state.selectedVehicleId.value = 2
    await run(state, requests, responder => { patchResponse = responder })
  } finally {
    app.unmount()
    for (const [key, descriptor] of Object.entries(previous)) {
      if (descriptor) Object.defineProperty(globalThis, key, descriptor)
      else delete globalThis[key]
    }
  }
}

test('maintenance saves the editable exchange reading without changing current mileage', () => setup(async (state, requests) => {
  state.openMaintenanceForm()
  assert.equal(state.maintenanceForm.value.mileage_km, 36200)
  state.maintenanceForm.value.mileage_km = 30000
  await state.saveMaintenance()
  assert.equal(requests[0].path, '/api/vehicles/2/maintenance')
  assert.equal(requests[0].body.mileage_km, 30000)
  assert.equal(state.selectedVehicle.value.mileage_km, 36200)
  assert.equal(state.maintenance.value[0].mileage_km, 30000)
  assert.equal(state.maintenanceFormOpen.value, false)

  state.selectedVehicleId.value = 3
  state.openMaintenanceForm()
  assert.equal(state.maintenanceForm.value.mileage_km, 12000)
  state.maintenanceForm.value.mileage_km = 9000
  await state.saveMaintenance()
  assert.equal(requests[1].path, '/api/vehicles/3/maintenance')
  assert.equal(requests[1].body.mileage_km, 9000)
  assert.equal(state.selectedVehicle.value.mileage_km, 12000)

  for (const mileage of [null, undefined, '', ' ', -1, 1.5, NaN, Infinity, 4294967296]) {
    state.openMaintenanceForm()
    state.maintenanceForm.value.mileage_km = mileage
    await state.saveMaintenance()
    assert.equal(requests.length, 2)
    assert.equal(state.maintenanceFormOpen.value, true)
  }
  // A missing current reading does not prevent recording a known exchange reading.
  state.selectedVehicle.value.mileage_km = null
  state.openMaintenanceForm()
  assert.equal(state.maintenanceForm.value.mileage_km, '')
  state.maintenanceForm.value.mileage_km = 0
  await state.saveMaintenance()
  assert.equal(requests[2].body.mileage_km, 0)
  assert.equal(state.selectedVehicle.value.mileage_km, null)
}))

test('settings updates the intended vehicle and keeps historical readings intact', () => setup(async (state, requests, respond) => {
  state.maintenance.value = [{ id: 1, mileage_km: 30000 }]
  await state.updateVehicleMileage(2, 42000)
  assert.deepEqual(requests[0], { path: '/api/vehicles/2/mileage', body: { mileage_km: 42000 } })
  assert.equal(state.selectedVehicle.value.mileage_km, 42000)
  assert.equal(state.maintenance.value[0].mileage_km, 30000)
  state.openMaintenanceForm()
  assert.equal(state.maintenanceForm.value.mileage_km, 42000)

  for (const invalid of [null, '', -1, 0.5, NaN, Infinity, 4294967296]) {
    await assert.rejects(state.updateVehicleMileage(2, invalid))
  }
  assert.equal(requests.length, 1)

  respond(() => new Response('{"detail":"저장 실패"}', { status: 500 }))
  await assert.rejects(state.updateVehicleMileage(2, 50000), /저장 실패/)
  assert.equal(state.selectedVehicle.value.mileage_km, 42000)

  let resolve
  respond(() => new Promise(done => { resolve = done }))
  const pending = state.updateVehicleMileage(2, 43000)
  state.selectedVehicleId.value = 3
  resolve(new Response('{"id":2,"mileage_km":43000}'))
  await pending
  assert.equal(state.vehicles.value[0].mileage_km, 43000)
  assert.equal(state.selectedVehicle.value.mileage_km, 12000)

  const signedOutRequest = state.updateVehicleMileage(2, 44000)
  await state.signOut()
  state.vehicles.value = [{ id: 2, mileage_km: 100 }]
  resolve(new Response('{"id":2,"mileage_km":44000}'))
  assert.equal(await signedOutRequest, null)
  assert.equal(state.vehicles.value[0].mileage_km, 100)
}))
