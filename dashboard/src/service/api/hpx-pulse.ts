import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { fetcher } from '@/service/http'

export type PulseGoal = 'stealth' | 'balanced' | 'speed'
export type PulseStatus =
  | 'pending_claim'
  | 'running'
  | 'stopped'
  | 'starting'
  | 'stopping'
  | 'error'
  | 'unhealthy'
  | 'partial'

export interface PulseProfileOption {
  profile_id: string
  title: string
  title_fa: string
  tunnel_mode: string
  carrier: string | null
  preset: string
  score: number
  reasons: string[]
  reasons_fa: string[]
  warnings: string[]
}

export interface PulseAdviseResponse {
  recommended_profile_id: string
  profiles: PulseProfileOption[]
  reality_front: {
    domain_on_iran: boolean
    sni: string | null
    dest: string
    checklist: string[]
    checklist_fa: string[]
  }
  warnings: string[]
}

export interface HpxPulseResponse {
  id: number
  name: string
  status: PulseStatus
  enabled: boolean
  engine: string
  profile_id: string
  goal: PulseGoal
  tunnel_mode: string
  carrier: string | null
  preset: string
  iran_public_ip: string
  abroad_public_ip: string
  control_port: number
  local_ip_iran: string
  local_ip_abroad: string
  port_forwards: string[]
  domain: string | null
  sni_hint: string | null
  note: string | null
  advice: PulseAdviseResponse | null
  iran_claimed: boolean
  abroad_claimed: boolean
  iran_agent_host: string | null
  abroad_agent_host: string | null
  iran_agent_last_seen: string | null
  abroad_agent_last_seen: string | null
  message: string | null
  created_at: string
}

export interface HpxPulsesResponse {
  pulses: HpxPulseResponse[]
  total: number
}

export interface PulseAdviseRequest {
  cpu_cores?: number
  ram_mb?: number
  udp_reachable?: boolean | null
  packet_loss_pct?: number | null
  goal?: PulseGoal
}

export interface HpxPulseCreate {
  name: string
  iran_public_ip: string
  abroad_public_ip: string
  goal?: PulseGoal
  cpu_cores?: number
  ram_mb?: number
  udp_reachable?: boolean | null
  packet_loss_pct?: number | null
  profile_id?: string | null
  control_port?: number
  port_forwards?: string[]
  domain?: string | null
  sni_hint?: string | null
  note?: string | null
}

export interface HpxPulseActionResponse {
  pulse: HpxPulseResponse
  message?: string | null
  iran_join_token?: string | null
  iran_join_command?: string | null
  abroad_join_token?: string | null
  abroad_join_command?: string | null
  iran_join_expires_at?: string | null
  abroad_join_expires_at?: string | null
}

export function useAdvisePulse() {
  return useMutation({
    mutationFn: (body: PulseAdviseRequest) =>
      fetcher<PulseAdviseResponse>('/api/hpx_pulse/advise', { method: 'POST', body }),
  })
}

export function useGetHpxPulses(params?: { offset?: number; limit?: number; name?: string }) {
  const q = new URLSearchParams()
  if (params?.offset != null) q.set('offset', String(params.offset))
  if (params?.limit != null) q.set('limit', String(params.limit))
  if (params?.name) q.set('name', params.name)
  const qs = q.toString()
  return useQuery({
    queryKey: ['hpx-pulses', params],
    queryFn: () => fetcher<HpxPulsesResponse>(`/api/hpx_pulses${qs ? `?${qs}` : ''}`),
    refetchInterval: 5000,
  })
}

export function useCreateHpxPulse() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: HpxPulseCreate) =>
      fetcher<HpxPulseActionResponse>('/api/hpx_pulse', { method: 'POST', body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['hpx-pulses'] }),
  })
}

export function useDeleteHpxPulse() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => fetcher<HpxPulseActionResponse>(`/api/hpx_pulse/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['hpx-pulses'] }),
  })
}

export function useRegeneratePulseTokens() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) =>
      fetcher<HpxPulseActionResponse>(`/api/hpx_pulse/${id}/join-token`, { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['hpx-pulses'] }),
  })
}
