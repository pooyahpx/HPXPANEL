import { cn } from '@/lib/utils'

type GradientLoaderProps = {
  className?: string
  size?: number
}

/** Soft spinning orb loader (no styled-components). */
export function GradientLoader({ className, size = 96 }: GradientLoaderProps) {
  return (
    <div className={cn('gradient-loader relative', className)} style={{ width: size, height: size }} aria-hidden>
      <div className="gradient-loader__orb">
        <span />
        <span />
        <span />
        <span />
      </div>
    </div>
  )
}
