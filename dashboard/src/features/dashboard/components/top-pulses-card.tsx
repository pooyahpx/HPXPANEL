import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
import { getPulseUsageShare } from '@/service/api/hpx-pulse'
import { formatBytes } from '@/utils/formatByte'
import { useQuery } from '@tanstack/react-query'
import { Activity, Lock, Trophy } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

const RANGES = [
  { key: '24h', hours: 24 },
  { key: '7d', hours: 24 * 7 },
  { key: '30d', hours: 24 * 30 },
  { key: '90d', hours: 24 * 90 },
] as const

type RangeKey = (typeof RANGES)[number]['key']

interface TopPulsesCardProps {
  canReadPulse: boolean
  className?: string
}

const TopPulsesCard = ({ canReadPulse, className }: TopPulsesCardProps) => {
  const { t } = useTranslation()
  const [range, setRange] = useState<RangeKey>('24h')

  const { data, isLoading, isError } = useQuery({
    queryKey: ['top-pulses-share', range],
    queryFn: ({ signal }) => {
      const hours = RANGES.find(item => item.key === range)?.hours ?? 24
      const start = new Date(Date.now() - hours * 3600 * 1000).toISOString()
      return getPulseUsageShare({ start }, signal)
    },
    enabled: canReadPulse,
    refetchInterval: 60_000,
    staleTime: 30_000,
    retry: false,
  })

  const items = (data?.items ?? []).filter(item => Number(item.bytes ?? 0) > 0)

  return (
    <Card className={cn('w-full', className)} data-testid="top-pulses-card">
      <CardHeader className="flex flex-col gap-3 space-y-0 pb-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 space-y-1">
          <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
            <Activity className="text-primary h-4 w-4 shrink-0 sm:h-5 sm:w-5" />
            {t('topPulses.title', { defaultValue: 'Most used Pulses' })}
          </CardTitle>
          <CardDescription className="text-xs sm:text-sm">
            {t('topPulses.subtitle', { defaultValue: 'Ranked by download + upload traffic per HPX Pulse' })}
          </CardDescription>
        </div>
        {canReadPulse && (
          <div className="flex shrink-0 flex-wrap gap-1" role="group" aria-label={t('topPulses.range', { defaultValue: 'Time range' })}>
            {RANGES.map(item => (
              <Button
                key={item.key}
                type="button"
                size="sm"
                variant={range === item.key ? 'default' : 'outline'}
                className="h-7 cursor-pointer px-2.5 text-xs"
                aria-pressed={range === item.key}
                onClick={() => setRange(item.key)}
              >
                {t(`topPulses.ranges.${item.key}`, {
                  defaultValue: item.key === '24h' ? 'Last 24h' : item.key === '7d' ? 'Last 7d' : item.key === '30d' ? 'Last 30d' : 'Last 90d',
                })}
              </Button>
            ))}
          </div>
        )}
      </CardHeader>
      <CardContent>
        {!canReadPulse ? (
          <div className="text-muted-foreground flex items-center gap-2 rounded-lg border border-dashed p-4 text-sm" data-testid="top-pulses-locked">
            <Lock className="h-4 w-4 shrink-0" />
            {t('topPulses.locked', { defaultValue: 'You need HPX Pulse read permission to see Pulse traffic ranking.' })}
          </div>
        ) : isLoading ? (
          <div className="space-y-3" data-testid="top-pulses-loading">
            {[0, 1, 2].map(i => (
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
          <div className="text-muted-foreground rounded-lg border border-dashed p-4 text-center text-sm">
            {t('topPulses.error', { defaultValue: 'Could not load Pulse usage.' })}
          </div>
        ) : items.length === 0 ? (
          <div className="text-muted-foreground flex flex-col items-center gap-2 rounded-lg border border-dashed p-6 text-center text-sm" data-testid="top-pulses-empty">
            <Activity className="h-6 w-6 opacity-50" />
            {t('topPulses.empty', { defaultValue: 'No Pulse traffic recorded in this period yet. Agents report usage on heartbeat.' })}
          </div>
        ) : (
          <ul className="space-y-3" data-testid="top-pulses-list">
            {items.map((item, index) => {
              const percent = Number(item.percent ?? 0)
              const color = index === 0 ? 'hsl(var(--primary))' : `hsl(var(--chart-${(index % 5) + 1}))`
              return (
                <li key={item.pulse_id} className="space-y-1.5">
                  <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 text-sm">
                    <span className="flex min-w-0 items-center gap-2">
                      <span className="bg-muted text-muted-foreground flex h-5 min-w-5 shrink-0 items-center justify-center rounded-full px-1 text-[11px] font-semibold tabular-nums">
                        {index + 1}
                      </span>
                      <span className="truncate font-medium" title={item.name}>
                        {item.name}
                      </span>
                      {index === 0 && (
                        <Badge variant="blue" className="shrink-0 gap-1 px-1.5 py-0 text-[10px] normal-case shadow-none">
                          <Trophy className="h-3 w-3" />
                          {t('topPulses.mostUsed', { defaultValue: 'Most used' })}
                        </Badge>
                      )}
                    </span>
                    <span dir="ltr" className="shrink-0 font-mono text-xs tabular-nums sm:text-sm">
                      <span className="font-semibold">{percent.toFixed(1)}%</span>
                      <span className="text-muted-foreground"> · {formatBytes(Number(item.bytes ?? 0))}</span>
                    </span>
                  </div>
                  <div className="bg-muted h-2 overflow-hidden rounded-full" dir="ltr">
                    <div
                      className="h-full rounded-full transition-all duration-200 motion-reduce:transition-none"
                      style={{ width: `${Math.min(100, Math.max(percent, 0))}%`, backgroundColor: color }}
                    />
                  </div>
                </li>
              )
            })}
          </ul>
        )}
        {canReadPulse && items.length > 0 && (
          <p className="text-muted-foreground mt-4 text-[11px]">
            {t('topPulses.total', { defaultValue: 'Total traffic' })}:{' '}
            <span dir="ltr" className="font-mono">
              {formatBytes(Number(data?.total_bytes ?? 0))}
            </span>
            {' · '}
            {t('topPulses.note', { defaultValue: 'Tracked from Pulse agents (prefer abroad). Download + upload.' })}
          </p>
        )}
      </CardContent>
    </Card>
  )
}

export default TopPulsesCard
