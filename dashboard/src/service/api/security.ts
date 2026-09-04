import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { fetcher } from '@/service/http'
import type { AdminDetails, Token } from '@/service/api'

export interface TOTPSetupResponse {
  secret: string
  otpauth_url: string
}

export interface AdminSessionItem {
  id: number
  user_agent?: string | null
  ip?: string | null
  created_at: string
  last_seen_at?: string | null
  current?: boolean
}

export interface AdminSessionsResponse {
  sessions: AdminSessionItem[]
}

export const adminTokenMfa = (body: { mfa_token: string; code: string }) =>
  fetcher<Token>('/api/admin/token/mfa', { method: 'POST', body })

export const setupTotp = () => fetcher<TOTPSetupResponse>('/api/admin/security/totp/setup', { method: 'POST' })

export const confirmTotp = (code: string) =>
  fetcher<AdminDetails>('/api/admin/security/totp/confirm', { method: 'POST', body: { code } })

export const disableTotp = (body: { code: string; password: string }) =>
  fetcher<AdminDetails>('/api/admin/security/totp/disable', { method: 'POST', body })

export const getAdminSessions = () => fetcher<AdminSessionsResponse>('/api/admin/security/sessions')

export const revokeAdminSession = (sessionId: number) =>
  fetcher<void>(`/api/admin/security/sessions/${sessionId}`, { method: 'DELETE' })

export const revokeOtherAdminSessions = () => fetcher<void>('/api/admin/security/sessions', { method: 'DELETE' })

export const useAdminTokenMfa = () =>
  useMutation({
    mutationFn: adminTokenMfa,
  })

export const useAdminSessions = () =>
  useQuery({
    queryKey: ['admin', 'security', 'sessions'],
    queryFn: getAdminSessions,
  })

export const useSetupTotp = () => useMutation({ mutationFn: setupTotp })

export const useConfirmTotp = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: confirmTotp,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/admin'] })
    },
  })
}

export const useDisableTotp = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: disableTotp,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/admin'] })
    },
  })
}

export const useRevokeAdminSession = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: revokeAdminSession,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'security', 'sessions'] })
    },
  })
}

export const useRevokeOtherAdminSessions = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: revokeOtherAdminSessions,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'security', 'sessions'] })
    },
  })
}
