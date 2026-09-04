import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import PageTransition from '@/components/layout/page-transition'
import HpxPulseList from '@/features/hpx-pulse/components/hpx-pulse-list'
import { useAdmin } from '@/hooks/use-admin'
import useDirDetection from '@/hooks/use-dir-detection'
import { cn } from '@/lib/utils'
import { useGetHpxPulses } from '@/service/api/hpx-pulse'
import { hasPermission } from '@/utils/rbac'
import { Activity, CircleAlert, Gauge, Plus, RadioTower, RefreshCw, Timer, Zap } from 'lucide-react'
import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'

export default function HpxPulsePage() {
  const { t } = useTranslation()
  const dir = useDirDetection()
  const { admin } = useAdmin()
  const canCreate = hasPermission(admin, 'hpx_pulse', 'create')
  const { data, isFetching, refetch } = useGetHpxPulses({ limit: 50, offset: 0 })

  const overview = useMemo(() => {
    const pulses = data?.pulses ?? []
    const running = pulses.filter(pulse => pulse.status === 'running').length
    const attention = pulses.filter(pulse =>
      ['error', 'unhealthy', 'partial'].includes(pulse.status),
    ).length
    const connectedAgents = pulses.reduce(
      (total, pulse) => total + Number(pulse.iran_claimed) + Number(pulse.abroad_claimed),
      0,
    )
    const expectedAgents = pulses.length * 2
    const autoSync = pulses.filter(pulse => Boolean(pulse.auto_restart_interval_minutes)).length
    const latencies = pulses
      .map(pulse => pulse.latency_ms)
      .filter((latency): latency is number => latency != null)
    const averagePing = latencies.length
      ? latencies.reduce((total, latency) => total + latency, 0) / latencies.length
      : null
    const healthPercent = pulses.length ? Math.round((running / pulses.length) * 100) : 0

    return {
      total: data?.total ?? 0,
      running,
      attention,
      connectedAgents,
      expectedAgents,
      autoSync,
      averagePing,
      healthPercent,
    }
  }, [data])

  const fleetHealthy = overview.total > 0 && overview.attention === 0

  return (
    <div className="flex min-h-0 w-full flex-1 flex-col items-start gap-0">
      <PageTransition isContentTransition className="w-full">
        <section dir={dir} className="relative w-full overflow-hidden border-b px-4 py-5 md:px-6 md:py-6">
          <div className="bg-primary/5 pointer-events-none absolute end-0 top-0 size-48 translate-x-1/3 -translate-y-1/2 rounded-full blur-3xl" />

          <div className="relative space-y-5">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="min-w-0 space-y-2">
                <div className="flex flex-wrap items-center gap-2">
                  <div className="bg-primary/10 text-primary flex size-9 items-center justify-center border border-primary/20">
                    <Zap className="size-4" />
                  </div>
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h1 className="font-display text-2xl font-bold tracking-tight sm:text-3xl">
                        {t('hpxPulse.title')}
                      </h1>
                      <Badge
                        variant="outline"
                        className={cn(
                          'h-6 gap-1.5 text-[10px] font-semibold tracking-wide uppercase',
                          fleetHealthy
                            ? 'border-emerald-500/35 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                            : overview.attention > 0
                              ? 'border-amber-500/35 bg-amber-500/10 text-amber-600 dark:text-amber-400'
                              : 'text-muted-foreground',
                        )}
                      >
                        <span
                          className={cn(
                            'size-1.5 rounded-full',
                            fleetHealthy
                              ? 'bg-emerald-500'
                              : overview.attention > 0
                                ? 'bg-amber-500'
                                : 'bg-muted-foreground/50',
                          )}
                        />
                        {fleetHealthy
                          ? t('hpxPulse.fleetHealthy', { defaultValue: 'Fleet healthy' })
                          : overview.attention > 0
                            ? t('hpxPulse.needsAttention', { defaultValue: 'Needs attention' })
                            : t('hpxPulse.noActiveTunnels', { defaultValue: 'No active tunnels' })}
                      </Badge>
                    </div>
                    <p className="text-muted-foreground mt-1 max-w-3xl text-xs leading-relaxed sm:text-sm">
                      {t('hpxPulse.description')}
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="h-9 w-9 p-0"
                  title={t('refresh', { defaultValue: 'Refresh' })}
                  onClick={() => void refetch()}
                  disabled={isFetching}
                >
                  <RefreshCw className={cn('size-3.5', isFetching && 'animate-spin')} />
                </Button>
                {canCreate && (
                  <Button
                    type="button"
                    size="sm"
                    className="h-9 gap-1.5"
                    onClick={() => window.dispatchEvent(new CustomEvent('openHpxPulseDialog'))}
                  >
                    <Plus className="size-3.5" />
                    {t('hpxPulse.add')}
                  </Button>
                )}
              </div>
            </div>

            <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-6">
              <Card className="border-border/70 bg-card/60 space-y-2 p-3 xl:col-span-2">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <Gauge className="text-primary size-4" />
                    <span className="text-xs font-medium">
                      {t('hpxPulse.fleetHealth', { defaultValue: 'Fleet health' })}
                    </span>
                  </div>
                  <span className="font-mono text-sm font-semibold tabular-nums">
                    {overview.healthPercent}%
                  </span>
                </div>
                <Progress
                  value={overview.healthPercent}
                  className="h-1.5"
                  indicatorClassName={overview.attention > 0 ? 'bg-amber-500' : 'bg-emerald-500'}
                />
                <p className="text-muted-foreground text-[10px]">
                  {t('hpxPulse.runningOfTotal', {
                    defaultValue: '{{running}} of {{total}} tunnels running',
                    running: overview.running,
                    total: overview.total,
                  })}
                </p>
              </Card>

              <Card className="border-border/70 bg-card/60 flex items-center gap-3 p-3">
                <div className="bg-emerald-500/10 text-emerald-600 flex size-8 items-center justify-center dark:text-emerald-400">
                  <Activity className="size-4" />
                </div>
                <div>
                  <p className="font-mono text-lg font-semibold leading-none tabular-nums">{overview.running}</p>
                  <p className="text-muted-foreground mt-1 text-[10px] uppercase tracking-wide">
                    {t('hpxPulse.runningLabel', { defaultValue: 'Running' })}
                  </p>
                </div>
              </Card>

              <Card className="border-border/70 bg-card/60 flex items-center gap-3 p-3">
                <div className={cn(
                  'flex size-8 items-center justify-center',
                  overview.attention > 0
                    ? 'bg-amber-500/10 text-amber-600 dark:text-amber-400'
                    : 'bg-muted text-muted-foreground',
                )}>
                  <CircleAlert className="size-4" />
                </div>
                <div>
                  <p className="font-mono text-lg font-semibold leading-none tabular-nums">{overview.attention}</p>
                  <p className="text-muted-foreground mt-1 text-[10px] uppercase tracking-wide">
                    {t('hpxPulse.attentionLabel', { defaultValue: 'Attention' })}
                  </p>
                </div>
              </Card>

              <Card className="border-border/70 bg-card/60 flex items-center gap-3 p-3">
                <div className="bg-sky-500/10 text-sky-600 flex size-8 items-center justify-center dark:text-sky-400">
                  <RadioTower className="size-4" />
                </div>
                <div>
                  <p className="font-mono text-lg font-semibold leading-none tabular-nums" dir="ltr">
                    {overview.connectedAgents}/{overview.expectedAgents}
                  </p>
                  <p className="text-muted-foreground mt-1 text-[10px] uppercase tracking-wide">
                    {t('hpxPulse.agentsOnline', { defaultValue: 'Agents online' })}
                  </p>
                </div>
              </Card>

              <Card className="border-border/70 bg-card/60 space-y-2 p-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Timer className="text-violet-500 size-4" />
                    <div>
                      <p className="font-mono text-lg font-semibold leading-none tabular-nums">
                        {overview.autoSync}
                      </p>
                      <p className="text-muted-foreground mt-1 text-[10px] uppercase tracking-wide">
                        {t('hpxPulse.autoSyncLabel', { defaultValue: 'Auto sync' })}
                      </p>
                    </div>
                  </div>
                  <div className="text-end">
                    <p className="font-mono text-xs font-semibold tabular-nums" dir="ltr">
                      {overview.averagePing != null ? `${overview.averagePing.toFixed(1)} ms` : '—'}
                    </p>
                    <p className="text-muted-foreground mt-1 text-[9px] uppercase tracking-wide">
                      {t('hpxPulse.avgPing', { defaultValue: 'Avg ping' })}
                    </p>
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </section>
      </PageTransition>
      <PageTransition isContentTransition className="flex min-h-0 flex-1 flex-col">
        <HpxPulseList />
      </PageTransition>
    </div>
  )
}
