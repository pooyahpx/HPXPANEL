import { cn } from '@/lib/utils'
import { Loader2 } from 'lucide-react'

interface LoadingSpinnerProps {
  text?: string
  size?: 'small' | 'medium' | 'large'
  className?: string
}

/**
 * Lightweight route / hydrate fallback.
 * Full gooey splash is only PageLoadOverlay (once per session) — avoids double-load feel.
 */
export function LoadingSpinner({ size = 'medium', className = '' }: LoadingSpinnerProps) {
  const icon = size === 'small' ? 'h-5 w-5' : size === 'large' ? 'h-9 w-9' : 'h-7 w-7'
  return (
    <div
      className={cn('flex min-h-[40vh] w-full flex-1 flex-col items-center justify-center gap-3 px-4 py-10', className)}
      role="status"
      aria-busy="true"
    >
      <Loader2 className={cn('text-primary animate-spin', icon)} />
      <span className="sr-only">Loading</span>
    </div>
  )
}
