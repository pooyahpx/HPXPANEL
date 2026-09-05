import { Card } from '@/components/ui/card'
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
  actionsMenu?: ReactNode
  onOpen: () => void
}

/**
 * Card shell for core editor entities — matches polished Nodes/Cores cards.
 */
export function CoreEditorListItemCard({ selectionControl, reorderGrip, selected = false, title, lines = [], actionsMenu, onOpen }: CoreEditorListItemCardProps) {
  return (
    <Card
      className={cn(
        'group hover:bg-accent/40 relative h-full max-w-full min-w-0 cursor-pointer overflow-hidden border p-4 transition-all duration-200 sm:p-5',
        selected && 'border-primary/50 bg-accent/30 ring-primary/20 ring-1',
      )}
      onClick={onOpen}
    >
      <div className="flex max-w-full min-w-0 items-start gap-3">
        {reorderGrip ? <div className="flex shrink-0 pt-0.5">{reorderGrip}</div> : null}
        {selectionControl ? <div className="pt-1.5">{selectionControl}</div> : null}
        <div className="flex max-w-full min-w-0 flex-1 items-start gap-3 overflow-hidden">
          <div className="min-w-0 flex-1 space-y-2.5 overflow-hidden">
            <div className="flex min-w-0 items-center gap-2 text-base font-semibold tracking-tight">{title}</div>
            {lines.length > 0 ? (
              <div className="bg-muted/30 border-border/50 space-y-1.5 rounded-lg border px-3 py-2.5">
                {lines.map((line, i) => (
                  <div key={i} className="text-muted-foreground min-w-0 text-xs leading-snug sm:text-[13px]">
                    {line}
                  </div>
                ))}
              </div>
            ) : null}
          </div>
          {actionsMenu ? <div className="flex shrink-0">{actionsMenu}</div> : null}
        </div>
      </div>
    </Card>
  )
}
