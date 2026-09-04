import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { fetcher } from '@/service/http'
import { regenerateHpxTunnelJoinToken } from '@/service/api/hpx-tunnels'

export interface FleetNodeSummary {
  id: number
  name: string
  status: string
  address?: string | null
  node_version?: string | null
  xray_version?: string | null
  last_status_change?: string | null
}

export interface FleetTunnelSummary {
  id: number
  name: string
  status: string
  agent_claimed: boolean
  agent_last_seen?: string | null
  agent_host?: string | null
}

export interface FleetPulseSummary {
  id: number
  name: string
  status: string
  iran_claimed: boolean
  abroad_claimed: boolean
  iran_agent_last_seen?: string | null
  abroad_agent_last_seen?: string | null
  iran_agent_host?: string | null
  abroad_agent_host?: string | null
}

export interface FleetSummary {
  generated_at: string
  nodes: FleetNodeSummary[]
  tunnels: FleetTunnelSummary[]
  pulses: FleetPulseSummary[]
  totals: {
    nodes: number
    tunnels: number
    pulses: number
  }
}

export const getFleetSummary = () => fetcher<FleetSummary>('/api/fleet/summary')

export const useFleetSummary = (options?: { enabled?: boolean; refetchInterval?: number | false }) =>
  useQuery({
    queryKey: ['fleet', 'summary'],
    queryFn: getFleetSummary,
    refetchInterval: options?.refetchInterval ?? 15_000,
    staleTime: 5_000,
    enabled: options?.enabled ?? true,
  })

export function useRegenerateFleetTunnelToken() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => regenerateHpxTunnelJoinToken(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['fleet', 'summary'] }),
  })
}

export function useRegenerateFleetPulseTokens() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => fetcher(`/api/hpx_pulse/${id}/join-token`, { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['fleet', 'summary'] }),
  })
}
