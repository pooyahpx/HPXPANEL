import { cn } from '@/lib/utils'
import { useId, useMemo } from 'react'

type MiniSparklineProps = {
  values: number[]
  className?: string
  strokeClassName?: string
  height?: number
}

export function MiniSparkline({ values, className, strokeClassName = 'stroke-sky-400', height = 36 }: MiniSparklineProps) {
  const gradId = useId()
  const path = useMemo(() => {
    if (values.length < 2) return ''
    const w = 100
    const h = height
    const min = Math.min(...values)
    const max = Math.max(...values)
    const span = max - min || 1
    const step = w / (values.length - 1)
    return values
      .map((v, i) => {
        const x = i * step
        const y = h - ((v - min) / span) * (h - 4) - 2
        return `${i === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`
      })
      .join(' ')
  }, [values, height])

  const areaPath = useMemo(() => {
    if (!path) return ''
    return `${path} L 100 ${height} L 0 ${height} Z`
  }, [path, height])

  if (values.length < 2) {
    return <div className={cn('bg-muted/30 h-9 w-full rounded-md', className)} aria-hidden />
  }

  return (
    <svg viewBox={`0 0 100 ${height}`} preserveAspectRatio="none" className={cn('h-9 w-full overflow-visible', className)} aria-hidden>
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="currentColor" stopOpacity="0.25" />
          <stop offset="100%" stopColor="currentColor" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={areaPath} className="text-sky-500/40" style={{ fill: `url(#${gradId})` }} />
      <path d={path} fill="none" className={cn('vector-effect-non-scaling-stroke', strokeClassName)} strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
