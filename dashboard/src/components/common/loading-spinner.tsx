import { GooeyLoader } from '@/components/ui/loader-10'
import { cn } from '@/lib/utils'

interface LoadingSpinnerProps {
  text?: string
  size?: 'small' | 'medium' | 'large'
  className?: string
}

const GOOEY_THEME = {
  primaryColor: '#38bdf8',
  secondaryColor: '#1e3a8a',
  borderColor: '#e2e8f0',
} as const

/**
 * Route / hydrate fallback — centered gooey loader.
 * First dashboard mount still uses PageLoadOverlay for the full splash.
 */
export function LoadingSpinner({ size = 'medium', className = '' }: LoadingSpinnerProps) {
  const scale = size === 'small' ? 'scale-75' : size === 'large' ? 'scale-125' : 'scale-100'
  return (
    <div
      className={cn('flex min-h-[50vh] w-full flex-1 flex-col items-center justify-center gap-6 px-4 py-12', className)}
      role="status"
      aria-busy="true"
    >
      <GooeyLoader {...GOOEY_THEME} className={scale} />
      <span className="sr-only">Loading</span>
    </div>
  )
}
