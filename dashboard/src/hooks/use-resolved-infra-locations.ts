import { useEffect, useMemo, useState } from 'react'
import {
  isPublicIp,
  lookupIpGeo,
  mergeInfraLocations,
  resolveInfraLocation,
  type InfraLocation,
} from '@/utils/infra-location'

type Locatable = {
  id: number | string
  name?: string | null
  address?: string | null
}

export const useResolvedInfraLocations = <T extends Locatable>(items: T[]) => {
  const nameBased = useMemo(() => {
    const map = new Map<string, InfraLocation>()
    for (const item of items) {
      map.set(String(item.id), resolveInfraLocation(item.name, item.address))
    }
    return map
  }, [items])

  const [geoBased, setGeoBased] = useState<Record<string, InfraLocation>>({})

  const geoLookupKey = useMemo(() => {
    return items
      .filter(item => {
        const current = nameBased.get(String(item.id))
        const needsCountry = !current?.countryCode
        const needsDc = !current?.datacenter
        return (needsCountry || needsDc) && isPublicIp(item.address)
      })
      .map(item => `${item.id}:${item.address!.trim()}`)
      .sort()
      .join('|')
  }, [items, nameBased])

  useEffect(() => {
    let cancelled = false
    if (!geoLookupKey) return

    const targets = geoLookupKey.split('|').map(entry => {
      const [id, ...ipParts] = entry.split(':')
      return { id, ip: ipParts.join(':') }
    })

    const run = async () => {
      const entries = await Promise.all(
        targets.map(async target => {
          const geo = await lookupIpGeo(target.ip)
          return geo ? ([target.id, geo] as const) : null
        }),
      )
      if (cancelled) return
      setGeoBased(prev => {
        const next = { ...prev }
        let changed = false
        for (const entry of entries) {
          if (!entry) continue
          const [id, geo] = entry
          const existing = next[id]
          if (
            existing?.countryCode === geo.countryCode &&
            existing?.datacenter === geo.datacenter &&
            existing?.flag === geo.flag
          ) {
            continue
          }
          next[id] = geo
          changed = true
        }
        return changed ? next : prev
      })
    }

    void run()
    return () => {
      cancelled = true
    }
  }, [geoLookupKey])

  return useMemo(() => {
    const map = new Map<string, InfraLocation>()
    for (const item of items) {
      const id = String(item.id)
      map.set(id, mergeInfraLocations(nameBased.get(id), geoBased[id]))
    }
    return map
  }, [items, nameBased, geoBased])
}
