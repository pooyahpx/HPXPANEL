import { orvalFetcher } from '../http'

export type IpGeoLookup = {
  ip: string
  country?: string | null
  country_code?: string | null
  city?: string | null
  isp?: string | null
  asn?: string | null
  source?: string
}

export const getSystemIpGeo = (host: string, signal?: AbortSignal) => {
  return orvalFetcher<IpGeoLookup>({
    url: `/api/system/ip-geo`,
    method: 'GET',
    params: { host },
    signal,
  })
}
