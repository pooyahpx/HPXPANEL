import { Card } from '@/components/ui/card'
import { CoreResponse } from '@/service/api'
import CoreActionsMenu from './core-actions-menu'
import { cn } from '@/lib/utils'
import type { ReactNode } from 'react'
import { Badge } from '@/components/ui/badge'
import { ArrowLeftRight, CalendarDays, Layers3, Network, ShieldCheck, Waypoints } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useMemo } from 'react'

interface CoreProps {
  core: CoreResponse
  onEdit: (core: CoreResponse) => void
  onToggleStatus: (core: CoreResponse) => Promise<void>
  onDuplicate?: () => void
  onDelete?: () => void
  canUpdate?: boolean
  canCreate?: boolean
  canDelete?: boolean
  selectionControl?: ReactNode
  selected?: boolean
}

function countInbounds(config: CoreResponse['config']): number {
  if (!config || typeof config !== 'object') return 0
  const inbounds = (config as { inbounds?: unknown }).inbounds
  return Array.isArray(inbounds) ? inbounds.length : 0
}

function countOutbounds(config: CoreResponse['config']): number {
  if (!config || typeof config !== 'object') return 0
  const outbounds = (config as { outbounds?: unknown }).outbounds
  return Array.isArray(outbounds) ? outbounds.length : 0
}

export default function Core({ core, onEdit, onDuplicate, onDelete, canUpdate = true, canCreate = true, canDelete = true, selectionControl, selected = false }: CoreProps) {
  const { t, i18n } = useTranslation()
  const type = String(core.type ?? 'xray')
  const TypeIcon = type === 'ikev2' ? ShieldCheck : type === 'l2tp' ? Network : type === 'wg' ? Waypoints : Layers3
  const inboundCount = useMemo(() => countInbounds(core.config), [core.config])
  const outboundCount = useMemo(() => countOutbounds(core.config), [core.config])
  const excludedCount = core.exclude_inbound_tags?.length ?? 0
  const fallbackCount = core.fallbacks_inbound_tags?.length ?? 0
  const createdLabel = useMemo(() => {
    if (!core.created_at) return null
    try {
      return new Intl.DateTimeFormat(i18n.language || undefined, { dateStyle: 'medium' }).format(new Date(core.created_at))
    } catch {
      return core.created_at.slice(0, 10)
    }
  }, [core.created_at, i18n.language])

  const typeTone =
    type === 'wg'
      ? 'border-cyan-500/30 bg-cyan-500/10 text-cyan-700 dark:text-cyan-300'
      : type === 'ikev2' || type === 'l2tp'
        ? 'border-violet-500/30 bg-violet-500/10 text-violet-700 dark:text-violet-300'
        : 'border-primary/30 bg-primary/10 text-primary'

  return (
    <Card
      className={cn(
        'group relative h-full overflow-hidden border transition-all duration-200',
        canUpdate && 'hover:bg-accent/40 cursor-pointer hover:shadow-sm',
        selected && 'border-primary/50 bg-accent/30 ring-primary/20 ring-1',
      )}
      onClick={() => {
        if (canUpdate) onEdit(core)
      }}
    >
      <div className="flex items-start gap-3 p-4 sm:p-5">
        {selectionControl ? <div className="pt-1.5">{selectionControl}</div> : null}
        <div className="min-w-0 flex-1 space-y-4">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1 space-y-2.5">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline" className={cn('h-6 gap-1.5 px-2 text-[10px] font-semibold tracking-wide uppercase', typeTone)}>
                  <TypeIcon className="h-3 w-3" />
                  {t(`coreTypes.${type}`, {
                    defaultValue: type === 'wg' ? 'WireGuard' : type === 'xray' ? 'Xray' : type.toUpperCase(),
                  })}
                </Badge>
                <Badge variant="outline" className="border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 h-6 gap-1.5 px-2 text-[10px] font-semibold tracking-wide uppercase">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                  {t('core.ready', { defaultValue: 'Ready' })}
                </Badge>
              </div>
              <h3 className="truncate text-base leading-tight font-semibold tracking-tight sm:text-lg">{core.name}</h3>
            </div>
            <CoreActionsMenu core={core} onEdit={onEdit} onDuplicate={onDuplicate} onDelete={onDelete} canUpdate={canUpdate} canCreate={canCreate} canDelete={canDelete} />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div className="bg-muted/35 border-border/50 rounded-lg border px-2.5 py-2">
              <div className="text-muted-foreground mb-1 flex items-center gap-1 text-[10px] font-medium tracking-wide uppercase">
                <Layers3 className="h-3 w-3" />
                {t('core.inbounds', { defaultValue: 'Inbounds' })}
              </div>
              <div className="text-sm font-semibold tabular-nums">{inboundCount}</div>
            </div>
            <div className="bg-muted/35 border-border/50 rounded-lg border px-2.5 py-2">
              <div className="text-muted-foreground mb-1 flex items-center gap-1 text-[10px] font-medium tracking-wide uppercase">
                <ArrowLeftRight className="h-3 w-3" />
                {t('core.outbounds', { defaultValue: 'Outbounds' })}
              </div>
              <div className="text-sm font-semibold tabular-nums">{outboundCount}</div>
            </div>
            <div className="bg-muted/35 border-border/50 rounded-lg border px-2.5 py-2">
              <div className="text-muted-foreground mb-1 text-[10px] font-medium tracking-wide uppercase">{t('core.excluded', { defaultValue: 'Excluded' })}</div>
              <div className="text-sm font-semibold tabular-nums">{excludedCount}</div>
            </div>
            <div className="bg-muted/35 border-border/50 rounded-lg border px-2.5 py-2">
              <div className="text-muted-foreground mb-1 text-[10px] font-medium tracking-wide uppercase">{t('core.fallbacks', { defaultValue: 'Fallbacks' })}</div>
              <div className="text-sm font-semibold tabular-nums">{fallbackCount}</div>
            </div>
          </div>

          {createdLabel ? (
            <div className="text-muted-foreground flex items-center gap-1.5 text-xs">
              <CalendarDays className="h-3.5 w-3.5 shrink-0" />
              <span>
                {t('core.created', { defaultValue: 'Created' })} · {createdLabel}
              </span>
            </div>
          ) : null}
        </div>
      </div>
    </Card>
  )
}
