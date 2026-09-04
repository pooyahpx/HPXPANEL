import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { $fetch, fetcher } from '@/service/http'

export type AuditResult = 'success' | 'failure'

export interface AuditLog {
  id: number
  actor_id?: number | null
  actor_username?: string | null
  source_ip?: string | null
  action: string
  resource: string
  resource_id?: string | null
  before?: Record<string, unknown> | unknown[] | null
  after?: Record<string, unknown> | unknown[] | null
  result: AuditResult
  detail?: string | null
  created_at: string
}

export interface AuditLogQuery {
  search?: string
  actor?: string
  action?: string
  resource?: string
  result?: AuditResult
  start?: string
  end?: string
  offset?: number
  limit?: number
}

export interface AuditLogsResponse {
  logs: AuditLog[]
  total: number
  offset: number
  limit: number
}

const cleanParams = (params: AuditLogQuery) => Object.fromEntries(Object.entries(params).filter(([, value]) => value !== undefined && value !== ''))

export const getAuditLogs = (params: AuditLogQuery) => fetcher<AuditLogsResponse>('/api/audit', { params: cleanParams(params) })

export const getAuditLog = (id: number) => fetcher<AuditLog>(`/api/audit/${id}`)

export const useAuditLogs = (params: AuditLogQuery, enabled = true) =>
  useQuery({
    queryKey: ['audit-logs', params],
    queryFn: () => getAuditLogs(params),
    placeholderData: keepPreviousData,
    enabled,
    staleTime: 10_000,
  })

export const useAuditLog = (id: number | null, enabled = true) =>
  useQuery({
    queryKey: ['audit-log', id],
    queryFn: () => getAuditLog(id as number),
    enabled: enabled && id !== null,
  })

export const downloadAuditCsv = async (params: AuditLogQuery) => {
  const blob = await $fetch<Blob>('/api/audit/export', {
    params: cleanParams(params),
    responseType: 'blob',
  })
  const href = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = href
  anchor.download = `audit-logs-${new Date().toISOString().slice(0, 10)}.csv`
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(href)
}
