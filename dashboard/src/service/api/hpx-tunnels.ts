import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { fetcher } from '@/service/http'

export type HpxTunnelRole = 'iran' | 'foreign'
export type HpxTunnelStatus = 'running' | 'stopped' | 'starting' | 'stopping' | 'error' | 'unhealthy' | 'pending_claim'

export interface HpxPortForward {
  external_port: number
  internal_ip: string
  internal_port: number
}

export interface HpxTunnelResponse {
  id: number
  name: string
  role: HpxTunnelRole
  status: HpxTunnelStatus
  enabled: boolean
  remote_ip?: string | null
  server_listen: string
  interface: string
  local_ip: string
  subnet: string
  mtu?: number | null
  keepalive: number
  dscp_mark?: number | null
  bandwidth_limit?: string | null
  operating_mode?: string | null
  port_forwards: HpxPortForward[]
  docker_image: string
  container_name: string
  backup_tunnel_id?: number | null
  auto_failover: boolean
  priority: number
  alert_on_down: boolean
  note?: string | null
  has_password: boolean
  agent_claimed?: boolean
  agent_host?: string | null
  agent_last_seen?: string | null
  agent_claimed_at?: string | null
  join_token_expires_at?: string | null
  last_health_check?: string | null
  latency_ms?: number | null
  packet_loss_pct?: number | null
  message?: string | null
  bytes_up: number
  bytes_down: number
  created_at: string
  last_status_change?: string | null
}

export interface HpxTunnelsResponse {
  tunnels: HpxTunnelResponse[]
  total: number
}

export interface HpxTunnelCreate {
  name: string
  role: HpxTunnelRole
  password: string
  enabled?: boolean
  remote_ip?: string | null
  server_listen?: string
  interface?: string
  local_ip?: string
  subnet?: string
  mtu?: number | null
  keepalive?: number
  dscp_mark?: number | null
  bandwidth_limit?: string | null
  operating_mode?: string | null
  port_forwards?: HpxPortForward[]
  docker_image?: string
  backup_tunnel_id?: number | null
  auto_failover?: boolean
  priority?: number
  alert_on_down?: boolean
  note?: string | null
  start_after_create?: boolean
}

export interface HpxTunnelUpdate extends Partial<Omit<HpxTunnelCreate, 'start_after_create'>> {}

export interface HpxTunnelActionResponse {
  tunnel: HpxTunnelResponse
  message?: string | null
  join_token?: string | null
  join_command?: string | null
  join_expires_at?: string | null
}

export interface HpxTunnelJoinTokenResponse {
  tunnel_id: number
  join_token: string
  join_command: string
  join_expires_at: string
}

export interface HpxTunnelStatsResponse {
  tunnel_id: number
  status: HpxTunnelStatus
  container_running: boolean
  interface_up: boolean
  interface_ip?: string | null
  latency_ms?: number | null
  packet_loss_pct?: number | null
  bytes_up: number
  bytes_down: number
  uptime_seconds?: number | null
  message?: string | null
}

const BASE = '/api/hpx_tunnel'

export const getHpxTunnelsQueryKey = (params?: Record<string, unknown>) => ['hpx-tunnels', params] as const
export const getHpxTunnelQueryKey = (id: number) => ['hpx-tunnel', id] as const

export const listHpxTunnels = (params?: Record<string, unknown>) =>
  fetcher<HpxTunnelsResponse>(`${BASE}s`, { params })

export const getHpxTunnel = (id: number) => fetcher<HpxTunnelResponse>(`${BASE}/${id}`)

export const createHpxTunnel = (data: HpxTunnelCreate) =>
  fetcher<HpxTunnelActionResponse>(BASE, { method: 'POST', body: data })

export const updateHpxTunnel = (id: number, data: HpxTunnelUpdate) =>
  fetcher<HpxTunnelResponse>(`${BASE}/${id}`, { method: 'PATCH', body: data })

export const deleteHpxTunnel = (id: number) => fetcher<void>(`${BASE}/${id}`, { method: 'DELETE' })

export const startHpxTunnel = (id: number) => fetcher<HpxTunnelActionResponse>(`${BASE}/${id}/start`, { method: 'POST' })

export const stopHpxTunnel = (id: number) => fetcher<HpxTunnelActionResponse>(`${BASE}/${id}/stop`, { method: 'POST' })

export const restartHpxTunnel = (id: number) => fetcher<HpxTunnelActionResponse>(`${BASE}/${id}/restart`, { method: 'POST' })

export const regenerateHpxTunnelJoinToken = (id: number) =>
  fetcher<HpxTunnelJoinTokenResponse>(`${BASE}/${id}/join-token`, { method: 'POST' })

export const getHpxTunnelStats = (id: number) => fetcher<HpxTunnelStatsResponse>(`${BASE}/${id}/stats`)

export const getHpxTunnelLogs = (id: number) => fetcher<string>(`${BASE}/${id}/logs`)

export function useGetHpxTunnels(params?: Record<string, unknown>, options?: { refetchInterval?: number }) {
  return useQuery({
    queryKey: getHpxTunnelsQueryKey(params),
    queryFn: () => listHpxTunnels(params),
    refetchInterval: options?.refetchInterval,
  })
}

export function useGetHpxTunnel(id: number, enabled = true) {
  return useQuery({
    queryKey: getHpxTunnelQueryKey(id),
    queryFn: () => getHpxTunnel(id),
    enabled: enabled && id > 0,
  })
}

export function useCreateHpxTunnel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: createHpxTunnel,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['hpx-tunnels'] }),
  })
}

export function useUpdateHpxTunnel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: HpxTunnelUpdate }) => updateHpxTunnel(id, data),
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: ['hpx-tunnels'] })
      qc.invalidateQueries({ queryKey: getHpxTunnelQueryKey(id) })
    },
  })
}

export function useDeleteHpxTunnel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: deleteHpxTunnel,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['hpx-tunnels'] }),
  })
}

export function useStartHpxTunnel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: startHpxTunnel,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['hpx-tunnels'] }),
  })
}

export function useStopHpxTunnel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: stopHpxTunnel,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['hpx-tunnels'] }),
  })
}

export function useRestartHpxTunnel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: restartHpxTunnel,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['hpx-tunnels'] }),
  })
}

export function useRegenerateHpxTunnelJoinToken() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: regenerateHpxTunnelJoinToken,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['hpx-tunnels'] }),
  })
}

export function useGetHpxTunnelStats(id: number, enabled = true) {
  return useQuery({
    queryKey: ['hpx-tunnel-stats', id],
    queryFn: () => getHpxTunnelStats(id),
    enabled: enabled && id > 0,
    refetchInterval: 15000,
  })
}
