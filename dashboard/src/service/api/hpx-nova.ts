import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { fetcher } from '@/service/http'

export type HpxNovaStatus =
  | 'pending_claim'
  | 'running'
  | 'stopped'
  | 'starting'
  | 'stopping'
  | 'error'
  | 'unhealthy'
  | 'partial'

export type HpxNovaCarrier = 'wss' | 'ws' | 'quic' | 'tcp' | 'tls'

export type HpxNovaResponse = {
  id: number
  name: string
  status: HpxNovaStatus
  enabled: boolean
  engine: string
  carrier: string
  lanes: number
  resume: boolean
  iran_public_ip: string
  abroad_public_ip: string
  tunnel_port: number
  sni?: string | null
  ws_path?: string | null
  port_forwards?: string[] | null
  proxy_listen?: string | null
  note?: string | null
  iran_claimed: boolean
  abroad_claimed: boolean
  iran_agent_online: boolean
  abroad_agent_online: boolean
  iran_agent_host?: string | null
  abroad_agent_host?: string | null
  latency_ms?: number | null
  message?: string | null
  created_at?: string | null
}

export type HpxNovaActionResponse = {
  detail: string
  nova?: HpxNovaResponse | null
  iran_join_token?: string | null
  abroad_join_token?: string | null
  iran_join_command?: string | null
  iran_join_command_alt?: string | null
  abroad_join_command?: string | null
  abroad_join_command_alt?: string | null
  join_expires_at?: string | null
}

export type HpxNovaCreate = {
  name: string
  iran_public_ip: string
  abroad_public_ip: string
  carrier?: HpxNovaCarrier
  lanes?: number
  resume?: boolean
  tunnel_port?: number
  sni?: string
  ws_path?: string
  port_forwards?: string[]
  proxy_listen?: string | null
  note?: string | null
}

export function useGetHpxNovas(params: { limit?: number; offset?: number } = {}, opts?: { enabled?: boolean }) {
  const qs = new URLSearchParams()
  if (params.limit != null) qs.set('limit', String(params.limit))
  if (params.offset != null) qs.set('offset', String(params.offset))
  const q = qs.toString()
  return useQuery({
    queryKey: ['hpx-novas', params],
    queryFn: () => fetcher<{ novas: HpxNovaResponse[]; total: number }>(`/api/hpx_novas${q ? `?${q}` : ''}`),
    enabled: opts?.enabled ?? true,
  })
}

export function useCreateHpxNova() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: HpxNovaCreate) =>
      fetcher<HpxNovaActionResponse>('/api/hpx_nova', { method: 'POST', body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['hpx-novas'] }),
  })
}

export function useDeleteHpxNova() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => fetcher<HpxNovaActionResponse>(`/api/hpx_nova/${id}`, { method: 'DELETE' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['hpx-novas'] }),
  })
}

export function useRegenerateNovaJoin() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => fetcher<HpxNovaActionResponse>(`/api/hpx_nova/${id}/join-token`, { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['hpx-novas'] }),
  })
}

export function useSyncHpxNova() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => fetcher<HpxNovaActionResponse>(`/api/hpx_nova/${id}/sync`, { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['hpx-novas'] }),
  })
}
