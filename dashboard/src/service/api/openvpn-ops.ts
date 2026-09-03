import { fetcher } from '@/service/http'

export interface OpenVPNUserMonitorEntry {
  user_id: number
  username: string
  has_certificate: boolean
  serial: string
  fingerprint: string
  online: boolean
  connection_count: number
  ips: Record<string, number>
  ip_protocol: Record<string, string>
}

export interface OpenVPNNodeMonitoringResponse {
  node_id: number
  core_id?: number | null
  core_name: string
  pki_ready: boolean
  listener_port?: number | null
  listener_proto: string
  users: OpenVPNUserMonitorEntry[]
}

export interface OpenVPNHealthCheck {
  core_id: number
  node_id?: number | null
  user_id?: number | null
  pki_ready: boolean
  ca_key_missing: boolean
  node_connected: boolean
  user_has_certificate: boolean
  user_in_openvpn_group: boolean
  host_configured: boolean
  ready: boolean
  issues: string[]
}

export interface OpenVPNOnboardingRequest {
  core_id: number
  node_id: number
  group_name?: string
  host_address: string
  host_port?: number
  test_username?: string
}

export interface OpenVPNOnboardingResponse {
  core_id: number
  node_id: number
  group_id: number
  host_id: number
  user_id: number
  username: string
  subscription_url: string
  health: OpenVPNHealthCheck
}

const BASE = '/api/openvpn'

export const getOpenVPNHealth = (params: { core_id: number; node_id?: number; user_id?: number }) => {
  const search = new URLSearchParams({ core_id: String(params.core_id) })
  if (params.node_id) search.set('node_id', String(params.node_id))
  if (params.user_id) search.set('user_id', String(params.user_id))
  return fetcher<OpenVPNHealthCheck>(`${BASE}/health?${search.toString()}`)
}

export const getOpenVPNNodeUsers = (nodeId: number) =>
  fetcher<OpenVPNNodeMonitoringResponse>(`${BASE}/node/${nodeId}/users`)

export const runOpenVPNOnboarding = (data: OpenVPNOnboardingRequest) =>
  fetcher<OpenVPNOnboardingResponse>(`${BASE}/onboarding`, { method: 'POST', body: data })

export function isOpenVPNPkiReady(config: Record<string, unknown> | undefined | null): boolean {
  if (!config) return false
  const caCert = String(config.ca_cert ?? '').trim()
  const caKey = String(config.ca_key ?? '').trim()
  const serverCert = String(config.server_cert ?? '').trim()
  const serverKey = String(config.server_key ?? '').trim()
  return Boolean(caCert && caKey && serverCert && serverKey)
}

export function isOpenVPNCaKeyMissing(config: Record<string, unknown> | undefined | null): boolean {
  if (!config) return false
  const caCert = String(config.ca_cert ?? '').trim()
  const caKey = String(config.ca_key ?? '').trim()
  return Boolean(caCert && !caKey)
}
