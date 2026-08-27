import { GradientLoader } from '@/components/ui/gradient-loader'
import { cn } from '@/lib/utils'

interface LoadingSpinnerProps {
  text?: string
  size?: 'small' | 'medium' | 'large'
  className?: string
}

/**
 * Route / hydrate fallback — uses the branded gradient orb (not the old bar).
 * First dashboard mount still uses PageLoadOverlay for the full splash.
 */
export function LoadingSpinner({ size = 'medium', className = '' }: LoadingSpinnerProps) {
  const orb = size === 'small' ? 48 : size === 'large' ? 96 : 72
  return (
    <div className={cn('flex min-h-[40vh] flex-1 flex-col items-center justify-center gap-4 px-4 py-10', className)} role="status" aria-busy="true">
      <GradientLoader size={orb} />
      <span className="sr-only">Loading</span>
    </div>
  )
}
