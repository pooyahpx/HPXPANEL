import { useEffect, useRef, useState } from 'react'

export type MetricHistoryPoint = {
  cpu: number
  mem: number
  disk: number
}

const MAX_POINTS = 36

/** Rolling window for dashboard sparklines (5s poll → ~3 min history). */
export function useMetricHistory(sample: MetricHistoryPoint | null) {
  const [series, setSeries] = useState<MetricHistoryPoint[]>([])
  const lastKey = useRef('')

  useEffect(() => {
    if (!sample) return
    const key = `${sample.cpu}|${sample.mem}|${sample.disk}`
    if (key === lastKey.current) return
    lastKey.current = key
    setSeries(prev => [...prev.slice(-(MAX_POINTS - 1)), sample])
  }, [sample])

  return series
}
