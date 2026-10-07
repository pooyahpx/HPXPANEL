import { useEffect, useMemo, useState } from 'react'
import { getSystemIpGeo } from '@/service/api/ip-geo'
import {
  countryFromCode,
  isPublicIp,
  mergeInfraLocations,
  resolveInfraLocation,
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

/** Resolve node location/datacenter from name hints + IP geo (panel backend). */
export const useResolvedInfraLocations = <T extends Locatable>(items: T[]) => {
  const [byId, setById] = useState<Record<string, InfraLocation>>({})

  const lookupKey = useMemo(() => {
    return items
      .map(item => `${item.id}:${(item.address || '').trim()}:${(item.name || '').trim()}`)
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
      const [id, ip = '', ...nameParts] = entry.split(':')
      return { id, ip, name: nameParts.join(':') }
    })

    const run = async () => {
      const entries = await Promise.all(
        targets.map(async target => {
          const fromName = resolveInfraLocation(target.name, target.ip)
          if (!isPublicIp(target.ip)) {
            return [target.id, fromName] as const
          }
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
            return [target.id, mergeInfraLocations(base, fromName)] as const
          } catch {
            return [target.id, fromName.countryCode ? fromName : emptyLocation()] as const
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
      const cached = byId[id]
      if (cached) {
        map.set(id, cached)
      } else {
        // Instant name-based hint while IP geo resolves
        map.set(id, resolveInfraLocation(item.name, item.address))
      }
    }
    return map
  }, [items, byId])
}
