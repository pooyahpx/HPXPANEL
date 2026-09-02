import { useMutation, useQueryClient } from '@tanstack/react-query'
import { fetcher } from '@/service/http'
import type { UserResponse } from '@/service/api'

export function userHasOpenVPNProfile(user: UserResponse): boolean {
  const openvpn = user.proxy_settings?.openvpn as { serial?: string; client_cert?: string } | undefined
  return Boolean(openvpn?.serial?.trim() || openvpn?.client_cert?.trim())
}

export const renewOpenVPNCertificate = (userId: number) =>
  fetcher<UserResponse>(`/api/user/by-id/${userId}/openvpn/renew`, { method: 'POST' })

export const revokeOpenVPNCertificate = (userId: number) =>
  fetcher<UserResponse>(`/api/user/by-id/${userId}/openvpn/revoke-cert`, { method: 'POST' })

export const useRenewOpenVPNCertificate = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: renewOpenVPNCertificate,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['/api/users'] })
    },
  })
}

export const useRevokeOpenVPNCertificate = () => {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: revokeOpenVPNCertificate,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['/api/users'] })
    },
  })
}
