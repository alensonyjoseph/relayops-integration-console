import { captureStep } from './api'
import type { ApiStep } from '../types'

export type Scenario = 'valid' | 'duplicate' | 'collision' | 'stale' | 'invalid' | 'malformed'

export async function runScenario(kind: Scenario): Promise<ApiStep[]> {
  if (kind === 'malformed') {
    return [await captureStep('Submit malformed JSON document', '/api/events',
      { source:'carrier_alpha', event_id:'bad-1', status:'DELIVERED', occurred_at:'not-a-date' })]
  }
  const ref = 'SHIP-LAB-' + crypto.randomUUID().slice(0, 8).toUpperCase()
  const id = 'lab-' + crypto.randomUUID().slice(0, 12)
  const steps: ApiStep[] = [
    await captureStep('Create synthetic shipment', '/api/shipments', { reference:ref, partner:'RelayOps Event Lab' }),
  ]
  if (steps[0].http !== 201) return steps

  const now = Date.now()
  const payload = {
    source: 'event_lab', event_id: id, shipment_ref: ref, status: 'PICKED_UP',
    occurred_at: new Date(now).toISOString(),
  }
  if (kind === 'invalid') {
    steps.push(await captureStep('Attempt invalid CREATED → DELIVERED', '/api/events',
      { ...payload, status:'DELIVERED' }))
    return steps
  }
  steps.push(await captureStep('Ingest initial valid PICKED_UP', '/api/events', payload))
  if (steps.at(-1)?.http !== 201 || kind === 'valid') return steps
  if (kind === 'duplicate') {
    steps.push(await captureStep('Replay identical event', '/api/events', payload))
  } else if (kind === 'collision') {
    steps.push(await captureStep('Replay same event ID with altered status', '/api/events',
      { ...payload, status:'DELIVERED' }))
  } else if (kind === 'stale') {
    steps.push(await captureStep('Send an older IN_TRANSIT event', '/api/events',
      { ...payload, event_id:id + '-late', status:'IN_TRANSIT',
        occurred_at:new Date(now - 60_000).toISOString() }))
  }
  return steps
}
