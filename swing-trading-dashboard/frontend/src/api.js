/**
 * API client — all requests proxied through Vite to http://localhost:8000
 */

const handleResponse = async (res) => {
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`API ${res.status}: ${text}`)
  }
  return res.json()
}

export const fetchRegime = () =>
  fetch('/api/regime').then(handleResponse)

export const fetchSetups = (type) =>
  fetch(`/api/setups/${type}`).then(handleResponse)

export const fetchAllSetups = () =>
  fetch('/api/setups').then(handleResponse)

export const fetchChartData = (ticker) =>
  fetch(`/api/chart/${ticker}`).then(handleResponse)

export const fetchSrZones = (ticker) =>
  fetch(`/api/sr-zones/${ticker}`).then(handleResponse)

export const triggerScan = () =>
  fetch('/api/run-scan', { method: 'POST' }).then(handleResponse)

export const fetchScanStatus = () =>
  fetch('/api/scan-status').then(handleResponse)
