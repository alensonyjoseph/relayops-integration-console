import type { OperationalEvent, Shipment, Metrics } from '../types'

export const sampleMetrics: Metrics = {
  shipments: 6, accepted: 10, rejected: 2, duplicates: 3, processed: 15,
}
export const sampleShipments: Shipment[] = [
  {reference:'SHIP-2048', partner:'Northstar Freight', status:'DELIVERED', version:3, created_at:null,last_event_at:null},
  {reference:'SHIP-2049', partner:'Meridian Express', status:'IN_TRANSIT', version:2, created_at:null,last_event_at:null},
  {reference:'SHIP-2050', partner:'Atlas Cargo', status:'IN_TRANSIT', version:2, created_at:null,last_event_at:null},
  {reference:'SHIP-2051', partner:'Northstar Freight', status:'PICKED_UP', version:1, created_at:null,last_event_at:null},
  {reference:'SHIP-2052', partner:'Helio Logistics', status:'PICKED_UP', version:1, created_at:null,last_event_at:null},
  {reference:'SHIP-2053', partner:'Meridian Express', status:'CREATED', version:0, created_at:null,last_event_at:null},
]
export const sampleEvents: OperationalEvent[] = [
  {event_id:'evt-1078',source:'carrier_alpha',shipment_ref:'SHIP-2048',requested_status:'DELIVERED', occurred_at:'',outcome:'ACCEPTED',rejection_reason:null,replay_count:0},
  {event_id:'evt-1077',source:'carrier_alpha',shipment_ref:'SHIP-2050',requested_status:'IN_TRANSIT',occurred_at:'',outcome:'ACCEPTED',rejection_reason:null,replay_count:0},
  {event_id:'evt-1076',source:'carrier_beta',shipment_ref:'SHIP-2048',requested_status:'PICKED_UP',occurred_at:'',outcome:'REJECTED',rejection_reason:'STALE_EVENT',replay_count:0},
  {event_id:'evt-1075',source:'carrier_alpha',shipment_ref:'SHIP-2051',requested_status:'PICKED_UP',occurred_at:'',outcome:'ACCEPTED',rejection_reason:null,replay_count:2},
]
export const scenarioDescriptions: Record<string, {title:string,subtitle:string,why:string}> = {
  valid: {title:'Valid transition', subtitle:'CREATED → PICKED_UP', why:'A correctly ordered event advances the shipment exactly once.'},
  duplicate: {title:'Exact duplicate', subtitle:'Retry without side effects', why:'The same external event and payload are acknowledged without a second transition.'},
  collision: {title:'Identifier collision', subtitle:'Same ID, modified payload', why:'The regression witness: blindly deduplicating by ID would hide a changed event.'},
  stale: {title:'Late event', subtitle:'Out-of-order delivery', why:'An older timestamp must not overwrite a newer accepted state.'},
  invalid: {title:'Invalid transition', subtitle:'CREATED → DELIVERED', why:'Domain rules reject an impossible state change and preserve the current state.'},
  malformed: {title:'Malformed request', subtitle:'Schema validation', why:'Invalid fields are rejected before database mutation.'},
}
