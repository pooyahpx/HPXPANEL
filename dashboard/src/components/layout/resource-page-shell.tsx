import { cn } from '@/lib/utils'
import { type ReactNode, useId } from 'react'

interface ResourcePageShellProps {
  children: ReactNode
  sectorIndex: string
  sectorLabel: string
  description: string
  stateLabel?: string
  telemetry?: ReactNode
  className?: string
  bodyClassName?: string
}

export default function ResourcePageShell({ children, sectorIndex, sectorLabel, description, stateLabel = 'Ready', telemetry, className, bodyClassName }: ResourcePageShellProps) {
  const headingId = useId()

  return (
    <div className={cn('mx-auto w-full max-w-[1680px] space-y-5 px-4 py-5 md:px-6 md:py-7', className)}>
      {telemetry && (
        <aside className="animate-slide-up transform-gpu" style={{ animationDuration: '500ms', animationDelay: '100ms', animationFillMode: 'both' }} aria-label={`${sectorLabel} telemetry`}>
          {telemetry}
        </aside>
      )}

      <section
        className="command-surface animate-slide-up transform-gpu"
        style={{ animationDuration: '500ms', animationDelay: telemetry ? '250ms' : '100ms', animationFillMode: 'both' }}
        aria-labelledby={headingId}
      >
        <header className="border-border flex flex-col gap-3 border-b px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex min-w-0 items-start gap-3">
            <span className="text-primary/60 pt-0.5 font-mono text-[10px] font-bold tracking-[0.16em]" aria-hidden="true">
              {sectorIndex}
            </span>
            <div className="min-w-0">
              <h2 id={headingId} className="text-primary font-mono text-[10px] font-bold tracking-[0.14em] uppercase">
                {sectorLabel}
              </h2>
              <p className="text-muted-foreground mt-1 text-xs leading-relaxed">{description}</p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2" role="status">
            <span className="online-beacon" aria-hidden="true" />
            <span className="font-mono text-[10px] font-bold tracking-[0.12em] uppercase">{stateLabel}</span>
          </div>
        </header>
        <div className={cn('p-3 sm:p-4', bodyClassName)}>{children}</div>
      </section>
    </div>
  )
}
