import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { $fetch, fetcher } from '@/service/http'

export interface BackupRemoteSftp {
  enabled: boolean
  host: string
  port: number
  username: string
  remote_path: string
}

export interface BackupConfig {
  auto_enabled: boolean
  schedule_hours: number
  local_retention: number
  upload_to_remote: boolean
  remote: BackupRemoteSftp
}

export interface BackupListItem {
  id: string
  created_at: string
  panel_version: string
  database_engine: string
  size_bytes: number
  sha256: string
  remote_uploaded: boolean
  filename: string
}

export interface BackupListResponse {
  items: BackupListItem[]
  status: 'idle' | 'running' | 'success' | 'failed'
  last_error: string
  last_success_at?: string | null
  config: BackupConfig
}

export const getBackups = () => fetcher<BackupListResponse>('/api/backup')

export const updateBackupConfig = (config: BackupConfig) =>
  fetcher<BackupConfig>('/api/backup/config', { method: 'PUT', body: config })

export const runBackup = () => fetcher<{ manifest: { id: string }; message: string }>('/api/backup/run', { method: 'POST' })

export const restoreBackup = (backupId: string) =>
  fetcher<{ success: boolean; message: string; restart_required: boolean }>(`/api/backup/${backupId}/restore`, { method: 'POST' })

export const importBackupArchive = async (file: File) => {
  const form = new FormData()
  form.append('file', file)
  return $fetch<{ manifest: { id: string }; message: string }>('/api/backup/import', { method: 'POST', body: form })
}

export const downloadBackupUrl = (backupId: string) => `/api/backup/${backupId}/download`

export const downloadBackupFile = async (backupId: string, filename: string) => {
  const blob = await $fetch<Blob>(downloadBackupUrl(backupId), { responseType: 'blob' })
  const url = window.URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  window.URL.revokeObjectURL(url)
}

export const useBackups = () =>
  useQuery({
    queryKey: ['backup', 'list'],
    queryFn: getBackups,
    refetchInterval: 5000,
  })

export const useUpdateBackupConfig = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: updateBackupConfig,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['backup', 'list'] }),
  })
}

export const useRunBackup = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: runBackup,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['backup', 'list'] }),
  })
}

export const useRestoreBackup = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: restoreBackup,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['backup', 'list'] }),
  })
}
