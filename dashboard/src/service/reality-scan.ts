import { orvalFetcher } from './http'

export interface RealityScanRequest {
  target: string
  timeout?: number | null
  check_iran_path?: boolean
}

export interface RealityPulsePathCheck {
  pulse_id: number
  name: string
  iran_ip: string
  port: number
  reachable: boolean
  latency_ms: number | null
  detail: string | null
}

export interface RealityIranPath {
  score: number
  grade: string
  iran_affinity: boolean
  affinity_reason: string | null
  pulse_checks: RealityPulsePathCheck[]
  notes: string[]
}

export interface RealityScanResult {
  target: string
  host: string
  ip: string | null
  port: number
  sni: string | null
  sni_discovered: boolean
  feasible: boolean
  tls13: boolean
  tls_version: string | null
  h2: boolean
  alpn: string | null
  x25519: boolean | null
  post_quantum: boolean | null
  curve: string | null
  h3: boolean
  cert_valid: boolean
  cert_subject: string | null
  cert_issuer: string | null
  not_after: string | null
  server_names: string[]
  latency_ms: number | null
  reason: string | null
  iran_path?: RealityIranPath | null
}

export interface RealityScanUsePayload {
  target: string
  serverNames: string[]
  sni: string | null
}

export const scanRealityTarget = (data: RealityScanRequest, signal?: AbortSignal) => {
  return orvalFetcher<RealityScanResult>({ url: '/api/core/reality-scan', method: 'POST', data, signal })
}

/** Curated REALITY decoys that usually pass TLS 1.3 + H2 + X25519. */
export const REALITY_PRESET_TARGETS: { host: string; label: string; region: 'global' | 'iran' }[] = [
  { host: 'digikala.com:443', label: 'Digikala', region: 'iran' },
  { host: 'www.digikala.com:443', label: 'Digikala www', region: 'iran' },
  { host: 'www.apple.com:443', label: 'Apple', region: 'global' },
  { host: 'www.microsoft.com:443', label: 'Microsoft', region: 'global' },
  { host: 'www.cloudflare.com:443', label: 'Cloudflare', region: 'global' },
  { host: 'cdnjs.cloudflare.com:443', label: 'cdnjs', region: 'global' },
  { host: 'dl.google.com:443', label: 'Google DL', region: 'global' },
  { host: 'www.samsung.com:443', label: 'Samsung', region: 'global' },
  { host: 'www.nvidia.com:443', label: 'NVIDIA', region: 'global' },
  { host: 'www.asus.com:443', label: 'ASUS', region: 'global' },
  { host: 'www.logitech.com:443', label: 'Logitech', region: 'global' },
  { host: 'www.speedtest.net:443', label: 'Speedtest', region: 'global' },
]

export function buildRealityUsePayload(result: RealityScanResult): RealityScanUsePayload {
  const target = `${result.host}:${result.port}`
  const names = new Set<string>()
  if (result.sni) names.add(result.sni)
  for (const name of result.server_names || []) {
    const trimmed = name.trim()
    if (trimmed) names.add(trimmed)
  }
  if (!names.size && result.host && !/^\d{1,3}(\.\d{1,3}){3}$/.test(result.host)) {
    names.add(result.host)
  }
  return { target, serverNames: [...names], sni: result.sni }
}
