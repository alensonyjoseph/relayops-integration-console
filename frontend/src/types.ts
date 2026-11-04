export type ShipmentStatus = 'CREATED' | 'PICKED_UP' | 'IN_TRANSIT' | 'DELIVERED' | 'CANCELLED'
export type EventOutcome = 'ACCEPTED' | 'REJECTED'
export type Tab = 'overview' | 'shipments' | 'laboratory' | 'diagnostics'

export interface Shipment {
  reference: string
  partner: string
  status: ShipmentStatus
  version: number
  created_at: string | null
  last_event_at: string | null
}
export interface OperationalEvent {
  id?: string
  source: string
  event_id: string
  shipment_ref: string
  requested_status: string
  occurred_at: string
  received_at?: string | null
  outcome: EventOutcome
  rejection_reason: string | null
  replay_count: number
}
export interface Metrics {
  shipments: number
  accepted: number
  rejected: number
  duplicates: number
  processed: number
}
export interface ApiStep {
  label: string
  request: unknown
  response: unknown
  http: number
}
export interface ApiError {
  code: string
  message: string
  fields?: string[]
}
