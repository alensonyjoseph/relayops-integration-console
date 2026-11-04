import type { ApiError, ApiStep } from '../types'

const KEY = 'relayops.workspace.v1'
function workspaceId(): string {
  let id = localStorage.getItem(KEY)
  if (!id || !/^[0-9a-f-]{36}$/i.test(id)) {
    id = crypto.randomUUID()
    localStorage.setItem(KEY, id)
  }
  return id
}

export class ApiFailure extends Error {
  status: number
  details: ApiError | null
  constructor(status: number, details: ApiError | null) {
    super(details?.message || 'Request failed')
    this.name = 'ApiFailure'
    this.status = status
    this.details = details
  }
}

export async function api<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method: body === undefined ? 'GET' : 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-RelayOps-Workspace': workspaceId(),
    },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    cache: 'no-store',
  })
  const payload: unknown = await response.json()
  if (!response.ok) {
    const parsed = payload as { error?: ApiError }
    throw new ApiFailure(response.status, parsed.error || null)
  }
  return payload as T
}

/** Scenario requests deliberately capture non-2xx domain outcomes instead of hiding them. */
export async function captureStep(label: string, path: string, body: unknown): Promise<ApiStep> {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-RelayOps-Workspace': workspaceId() },
    body: JSON.stringify(body),
    cache: 'no-store',
  })
  const payload = await response.json() as unknown
  return { label, request: body, response: payload, http: response.status }
}
