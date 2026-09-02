import { useQuery } from '@tanstack/react-query'
import { fetcher } from '@/service/http'

export type ProtocolHealthStatus = 'healthy' | 'degraded' | 'down' | 'unknown'

export interface ProtocolHealth {
  protocol: string
  status: ProtocolHealthStatus
  latency_ms?: number | null
  detail?: string
}

export interface NodeObservabilityCard {
  node_id: number
  name: string
  address: string
  status: string
  cpu_usage?: number | null
  mem_usage_percent?: number | null
  incoming_mbps?: number | null
  outgoing_mbps?: number | null
  uptime_seconds?: number | null
  users_total: number
  users_online: number
  protocols: ProtocolHealth[]
  packet_loss_percent?: number | null
  latency_ms?: number | null
}

export interface MasterObservabilityCard {
  resources: {
    version: string
    uptime_seconds: number
    mem_total: number
    mem_used: number
    disk_total: number
    disk_used: number
    cpu_cores: number
    cpu_usage: number
  }
  users: {
    total_user: number
    online_users: number
    active_users: number
    disabled_users: number
    expired_users: number
    limited_users: number
    on_hold_users: number
    incoming_bandwidth: number
    outgoing_bandwidth: number
  }
  protocols: ProtocolHealth[]
}

export interface ObservabilityAlertEvent {
  id: number
  scope: string
  node_id?: number | null
  node_name?: string | null
  metric: string
  value: number
  threshold: number
  message: string
  created_at: string
}

export interface ObservabilitySummary {
  generated_at: string
  master?: MasterObservabilityCard | null
  nodes: NodeObservabilityCard[]
  workers?: {
    scheduler: { status: string; response_time_ms?: number | null; error?: string | null }
    node: { status: string; response_time_ms?: number | null; error?: string | null }
  } | null
  recent_alerts: ObservabilityAlertEvent[]
  node_stats_recording_enabled: boolean
}

export interface SystemStatsHistoryPoint {
  period_start: string
  cpu_usage_percentage: number
  mem_usage_percentage: number
  incoming_mbps: number
  outgoing_mbps: number
}

export interface SystemStatsHistory {
  scope: string
  node_id?: number | null
  stats: SystemStatsHistoryPoint[]
}

export const getObservabilitySummary = () => fetcher<ObservabilitySummary>('/api/observability/summary')

export const getObservabilityHistory = (params?: { node_id?: number; hours?: number }) =>
  fetcher<SystemStatsHistory>('/api/observability/history', { params })

export const useObservabilitySummary = (options?: { enabled?: boolean; refetchInterval?: number | false }) =>
  useQuery({
    queryKey: ['observability', 'summary'],
    queryFn: getObservabilitySummary,
    refetchInterval: options?.refetchInterval ?? 2000,
    staleTime: 1000,
    enabled: options?.enabled ?? true,
  })

export const useObservabilityHistory = (
  params?: { node_id?: number; hours?: number },
  options?: { enabled?: boolean },
) =>
  useQuery({
    queryKey: ['observability', 'history', params?.node_id ?? 'master', params?.hours ?? 24],
    queryFn: () => getObservabilityHistory(params),
    enabled: options?.enabled ?? true,
    staleTime: 30_000,
  })
