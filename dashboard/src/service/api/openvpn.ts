import { fetcher } from '@/service/http'

export interface OpenVPNPkiBundle {
  ca_cert: string
  ca_key: string
  server_cert: string
  server_key: string
  tls_crypt_key: string
}

export interface OpenVPNPkiRequest {
  ca_common_name?: string
  server_common_name?: string
}

export const generateOpenVPNPki = (data: OpenVPNPkiRequest = {}) =>
  fetcher<OpenVPNPkiBundle>('/api/core/openvpn/generate-pki', { method: 'POST', body: data })
