import { useEffect, useMemo, useState } from 'react'
import { getSystemIpGeo } from '@/service/api/ip-geo'
import {
  countryFromCode,
  isPublicIp,
  type InfraLocation,
} from '@/utils/infra-location'

type Locatable = {
  id: number | string
  name?: string | null
  address?: string | null
}

const emptyLocation = (): InfraLocation => ({
  countryCode: null,
  countryEn: null,
  countryFa: null,
  flag: null,
  datacenter: null,
})

/** Resolve node location/datacenter from IP via check-host.net (panel backend). */
export const useResolvedInfraLocations = <T extends Locatable>(items: T[]) => {
  const [byId, setById] = useState<Record<string, InfraLocation>>({})

  const lookupKey = useMemo(() => {
    return items
      .filter(item => isPublicIp(item.address))
      .map(item => `${item.id}:${item.address!.trim()}`)
      .sort()
      .join('|')
  }, [items])

  useEffect(() => {
    let cancelled = false
    if (!lookupKey) {
      setById({})
      return
    }

    const targets = lookupKey.split('|').map(entry => {
      const [id, ...ipParts] = entry.split(':')
      return { id, ip: ipParts.join(':') }
    })

    const run = async () => {
      const entries = await Promise.all(
        targets.map(async target => {
          try {
            const geo = await getSystemIpGeo(target.ip)
            const base = countryFromCode(geo.country_code)
            if (!base.countryCode && geo.country) {
              base.countryEn = geo.country
              base.countryCode = geo.country_code?.toUpperCase() || null
            } else if (geo.country) {
              base.countryEn = geo.country
            }
            base.city = geo.city || null
            base.datacenter = (geo.isp || '').trim() || null
            return [target.id, base] as const
          } catch {
            return [target.id, emptyLocation()] as const
          }
        }),
      )
      if (cancelled) return
      const next: Record<string, InfraLocation> = {}
      for (const [id, location] of entries) {
        next[id] = location
      }
      setById(next)
    }

    void run()
    return () => {
      cancelled = true
    }
  }, [lookupKey])

  return useMemo(() => {
    const map = new Map<string, InfraLocation>()
    for (const item of items) {
      const id = String(item.id)
      map.set(id, byId[id] || emptyLocation())
    }
    return map
  }, [items, byId])
}
