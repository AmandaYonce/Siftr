import type { ClustersResponse, ScanResponse } from './types'

export class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, init)
  } catch {
    throw new ApiError('Cannot reach the Siftr backend. Is it running on port 8000?')
  }
  const body: unknown = await res.json().catch(() => null)
  if (!res.ok) {
    const message =
      body && typeof body === 'object' && 'error' in body && typeof body.error === 'string'
        ? body.error
        : `Request failed with status ${res.status}`
    throw new ApiError(message)
  }
  return body as T
}

export function scanFolder(
  folder: string,
  threshold: number,
  recursive: boolean,
): Promise<ScanResponse> {
  return request('/api/scan', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ folder, threshold, recursive }),
  })
}

export function fetchClusters(threshold: number): Promise<ClustersResponse> {
  return request(`/api/clusters?threshold=${threshold}`)
}

export function postDecisions(reject: number[]): Promise<{ ok: boolean }> {
  return request('/api/decisions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reject }),
  })
}
