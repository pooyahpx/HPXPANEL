import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { getUsersUsageShare } from '@/service/api'
import { formatBytes } from '@/utils/formatByte'
import { useQuery } from '@tanstack/react-query'
import { Lock, PieChart as PieChartIcon, Trophy } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

const RANGES = [
  { key: '24h', hours: 24 },
  { key: '7d', hours: 24 * 7 },
  { key: '30d', hours: 24 * 30 },
  { key: '90d', hours: 24 * 90 },
] as const

type RangeKey = (typeof RANGES)[number]['key']

interface TopConfigsCardProps {
  /** Limit the ranking to users owned by this admin (sudo filter). Undefined = everything the viewer can read. */
  adminUsername?: string
  /** Per-node breakdown requires the `nodes.stats` permission. */
  canReadNodeStats: boolean
  className?: string
}

const TopConfigsCard = ({ adminUsername, canReadNodeStats, className }: TopConfigsCardProps) => {
  const { t } = useTranslation()
  const [range, setRange] = useState<RangeKey>('7d')

  const { data, isLoading, isError } = useQuery({
    queryKey: ['top-configs-share', range, adminUsername ?? null],
    queryFn: ({ signal }) => {
      const hours = RANGES.find(item => item.key === range)?.hours ?? 24 * 7
      // `end` is omitted so the server uses "now"; `start` is resolved at fetch time so refetches stay fresh.
      const start = new Date(Date.now() - hours * 3600 * 1000).toISOString()
      return getUsersUsageShare({ start, ...(adminUsername ? { admin: [adminUsername] } : {}) }, signal)
    },
    enabled: canReadNodeStats,
    refetchInterval: 60_000,
    staleTime: 30_000,
    retry: false,
  })

  const items = (data?.items ?? []).filter(item => Number(item.bytes ?? 0) > 0)

  return (
    <Card className={cn('w-full', className)} data-testid="top-configs-card">
      <CardHeader className="flex flex-col gap-3 space-y-0 pb-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 space-y-1">
          <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
            <PieChartIcon className="text-primary h-4 w-4 shrink-0 sm:h-5 sm:w-5" />
            {t('topConfigs.title', { defaultValue: 'Most used configs' })}
          </CardTitle>
          <CardDescription className="text-xs sm:text-sm">
            {t('topConfigs.subtitle', { defaultValue: 'Ranked by traffic share per server (node/path)' })}
            {adminUsername ? ` · ${adminUsername}` : ''}
          </CardDescription>
        </div>
        {canReadNodeStats && (
          <div className="flex shrink-0 flex-wrap gap-1" role="group" aria-label={t('topConfigs.range', { defaultValue: 'Time range' })}>
            {RANGES.map(item => (
              <Button
                key={item.key}
                type="button"
                size="sm"
                variant={range === item.key ? 'default' : 'outline'}
                className="h-7 px-2.5 text-xs"
                aria-pressed={range === item.key}
                onClick={() => setRange(item.key)}
              >
                {t(`topConfigs.ranges.${item.key}`, { defaultValue: item.key })}
              </Button>
            ))}
          </div>
        )}
      </CardHeader>
      <CardContent>
        {!canReadNodeStats ? (
          <div className="text-muted-foreground flex items-center gap-2 rounded-lg border border-dashed p-4 text-sm" data-testid="top-configs-locked">
            <Lock className="h-4 w-4 shrink-0" />
            {t('topConfigs.locked', { defaultValue: 'You need the "node statistics" permission to see which configs are used the most.' })}
          </div>
        ) : isLoading ? (
          <div className="space-y-3" data-testid="top-configs-loading">
            {[0, 1, 2, 3].map(i => (
              <div key={i} className="space-y-1.5">
                <div className="flex items-center justify-between gap-2">
                  <Skeleton className="h-4 w-1/3" />
                  <Skeleton className="h-4 w-20" />
                </div>
                <Skeleton className="h-2 w-full rounded-full" />
              </div>
            ))}
          </div>
        ) : isError ? (
          <div className="text-muted-foreground rounded-lg border border-dashed p-4 text-center text-sm">{t('topConfigs.error', { defaultValue: 'Could not load config usage.' })}</div>
        ) : items.length === 0 ? (
          <div className="text-muted-foreground flex flex-col items-center gap-2 rounded-lg border border-dashed p-6 text-center text-sm" data-testid="top-configs-empty">
            <PieChartIcon className="h-6 w-6 opacity-50" />
            {t('topConfigs.empty', { defaultValue: 'No traffic recorded in this period.' })}
          </div>
        ) : (
          <ul className="space-y-3" data-testid="top-configs-list">
            {items.map((item, index) => {
              const percent = Number(item.percent ?? 0)
              const color = index === 0 ? 'hsl(var(--primary))' : `hsl(var(--chart-${(index % 5) + 1}))`
              return (
                <li key={`${item.node_id ?? 'panel'}-${item.name}`} className="space-y-1.5">
                  <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 text-sm">
                    <span className="flex min-w-0 items-center gap-2">
                      <span className="bg-muted text-muted-foreground flex h-5 min-w-5 shrink-0 items-center justify-center rounded-full px-1 text-[11px] font-semibold tabular-nums">{index + 1}</span>
                      <span className="truncate font-medium" title={item.name}>
                        {item.name}
                      </span>
                      {index === 0 && (
                        <Badge variant="blue" className="shrink-0 gap-1 px-1.5 py-0 text-[10px] normal-case shadow-none">
                          <Trophy className="h-3 w-3" />
                          {t('topConfigs.mostUsed', { defaultValue: 'Most used' })}
                        </Badge>
                      )}
                    </span>
                    <span dir="ltr" className="shrink-0 font-mono text-xs tabular-nums sm:text-sm">
                      <span className="font-semibold">{percent.toFixed(1)}%</span>
                      <span className="text-muted-foreground"> · {formatBytes(Number(item.bytes ?? 0))}</span>
                    </span>
                  </div>
                  <div className="bg-muted h-2 overflow-hidden rounded-full" dir="ltr">
                    <div className="h-full rounded-full transition-all" style={{ width: `${Math.min(100, Math.max(percent, 0))}%`, backgroundColor: color }} />
                  </div>
                </li>
              )
            })}
          </ul>
        )}
        {canReadNodeStats && items.length > 0 && (
          <p className="text-muted-foreground mt-4 text-[11px]">
            {t('topConfigs.total', { defaultValue: 'Total traffic' })}:{' '}
            <span dir="ltr" className="font-mono">
              {formatBytes(Number(data?.total_bytes ?? 0))}
            </span>
            {' · '}
            {t('topConfigs.note', { defaultValue: 'Traffic is tracked per server (node), not per inbound.' })}
          </p>
        )}
      </CardContent>
    </Card>
  )
}

export default TopConfigsCard
