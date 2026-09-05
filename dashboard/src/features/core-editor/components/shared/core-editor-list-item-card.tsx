import { cn } from '@/lib/utils'
import type { ReactNode } from 'react'

export interface CoreEditorListItemCardProps {
  selectionControl?: ReactNode
  /** Grip handle injected when using {@link CoreEditorSortableGridCard} (grid DnD). */
  reorderGrip?: ReactNode
  /** Checkbox / bulk selection styling (aligned with cores list). */
  selected?: boolean
  /** Primary headline. */
  title: ReactNode
  /** Secondary lines (protocol, ports, tags, …). */
  lines?: ReactNode[]
  /** Optional hero metric shown large on the trailing edge (e.g. port). */
  hero?: ReactNode
  actionsMenu?: ReactNode
  onOpen: () => void
}

/**
 * Signal-tile card for core-editor entities — command-surface chrome, accent rail, hero metric.
 */
export function CoreEditorListItemCard({ selectionControl, reorderGrip, selected = false, title, lines = [], hero, actionsMenu, onOpen }: CoreEditorListItemCardProps) {
  return (
    <button
      type="button"
      onClick={onOpen}
      className={cn(
        'command-surface group relative flex h-full max-w-full min-w-0 w-full cursor-pointer flex-col overflow-hidden text-start transition-colors',
        'hover:bg-accent/30 focus-visible:ring-ring focus-visible:ring-2 focus-visible:outline-none',
        selected && 'border-primary bg-accent/25 ring-primary/25 ring-1',
      )}
    >
      <span className="bg-primary absolute inset-y-0 start-0 w-1" aria-hidden="true" />
      <div className="flex max-w-full min-w-0 flex-1 items-stretch gap-0 ps-1">
        {(reorderGrip || selectionControl) && (
          <div className="border-border/60 flex shrink-0 flex-col items-center gap-2 border-e px-2 py-4">
            {reorderGrip}
            {selectionControl}
          </div>
        )}
        <div className="flex min-w-0 flex-1 flex-col gap-3 p-4 sm:p-5">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1 space-y-2">
              <div className="font-display truncate text-lg leading-tight font-bold tracking-tight sm:text-xl">{title}</div>
              {lines.length > 0 ? (
                <div className="flex flex-wrap items-center gap-2">
                  {lines.map((line, i) => (
                    <div key={i} className="min-w-0">
                      {line}
                    </div>
                  ))}
                </div>
              ) : null}
            </div>
            {actionsMenu ? (
              <div
                className="flex shrink-0"
                onClick={e => {
                  e.stopPropagation()
                }}
              >
                {actionsMenu}
              </div>
            ) : null}
          </div>
          {hero ? (
            <div className="border-border/70 bg-muted/25 mt-auto flex items-end justify-between gap-3 border-t pt-3">
              <span className="text-muted-foreground font-mono text-[10px] font-bold tracking-[0.16em] uppercase">Channel</span>
              <div className="font-display text-primary text-2xl leading-none font-black tracking-tight tabular-nums sm:text-3xl">{hero}</div>
            </div>
          ) : null}
        </div>
      </div>
    </button>
  )
}
