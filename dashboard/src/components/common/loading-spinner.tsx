import { cn } from '@/lib/utils'

interface LoadingSpinnerProps {
  text?: string
  size?: 'small' | 'medium' | 'large'
  className?: string
}

/**
 * Lightweight route fallback — no full-screen overlay.
 * TopLoadingBar already signals navigation progress.
 */
export function LoadingSpinner({ className = '' }: LoadingSpinnerProps) {
  return (
    <div className={cn('flex min-h-[32vh] flex-1 items-center justify-center px-4 py-10', className)} role="status" aria-busy="true">
      <div className="border-border bg-muted relative h-1.5 w-28 overflow-hidden border">
        <div className="bg-primary absolute inset-y-0 w-1/2 animate-[pulse_0.9s_ease-in-out_infinite]" />
      </div>
      <span className="sr-only">Loading</span>
    </div>
  )
}
