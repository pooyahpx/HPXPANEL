import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import PageTransition from '@/components/layout/page-transition'
import HpxPulseList from '@/features/hpx-pulse/components/hpx-pulse-list'
import HpxTunnelsList from '@/features/hpx-tunnels/components/hpx-tunnels-list'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useAdmin } from '@/hooks/use-admin'
import useDirDetection from '@/hooks/use-dir-detection'
import { cn } from '@/lib/utils'
import { useGetHpxPulses } from '@/service/api/hpx-pulse'
import { fetcher } from '@/service/http'
import { canReadResourcePage, hasPermission } from '@/utils/rbac'
import { Activity, CircleAlert, Gauge, Plus, Radar, RadioTower, RefreshCw, Timer, Zap } from 'lucide-react'
import { useEffect, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router'

export default function HpxPulsePage() {
  const { t } = useTranslation()
  const dir = useDirDetection()
  const { admin } = useAdmin()
  const canCreate = hasPermission(admin, 'hpx_pulse', 'create')
  const canCreateIcmp = hasPermission(admin, 'hpx_tunnels', 'create')
  const canReadPulse = canReadResourcePage(admin, 'hpx_pulse')
  const canReadIcmp = canReadResourcePage(admin, 'hpx_tunnels')
  const showPulseTab = canReadPulse
  const showIcmpTab = canReadIcmp
  const [searchParams, setSearchParams] = useSearchParams()
  const tabParam = searchParams.get('tab')
  const activeTab = tabParam === 'icmp' && showIcmpTab ? 'icmp' : showPulseTab ? 'pulse' : 'icmp'
  const { data, isFetching, refetch } = useGetHpxPulses({ limit: 50, offset: 0 }, { enabled: showPulseTab })
  const { data: engineInfo } = useQuery({
    queryKey: ['hpx-pulse-engine'],
    queryFn: () => fetcher('/api/hpx_pulse/engine', { method: 'GET' }) as Promise<{ engine_version: string; release_tag: string }>,
    staleTime: 60_000,
  })

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

  useEffect(() => {
    if (tabParam === 'icmp' && !showIcmpTab) {
      setSearchParams({}, { replace: true })
    }
    if (tabParam !== 'icmp' && !showPulseTab && showIcmpTab) {
      setSearchParams({ tab: 'icmp' }, { replace: true })
    }
  }, [tabParam, showIcmpTab, showPulseTab, setSearchParams])

  return (
    <div className="flex min-h-0 w-full flex-1 flex-col items-start gap-0">
      <PageTransition isContentTransition className="w-full">
        <section dir={dir} className="relative w-full overflow-hidden border-b border-white/5 px-4 py-6 md:px-6 md:py-8">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,hsl(var(--mesh-a)/0.55),transparent_55%),radial-gradient(ellipse_at_bottom_left,hsl(var(--mesh-c)/0.45),transparent_50%)]" />
          <div className="bg-primary/20 pointer-events-none absolute end-[-4rem] top-[-3rem] size-64 rounded-full blur-3xl" />
          <div className="pointer-events-none absolute start-[-3rem] bottom-[-4rem] size-56 rounded-full bg-emerald-500/10 blur-3xl" />

          <div className="relative space-y-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="min-w-0 space-y-2">
                <div className="flex flex-wrap items-center gap-3">
                  <div className="bg-primary/15 text-primary flex size-11 items-center justify-center rounded-2xl border border-primary/25 shadow-lg shadow-primary/10">
                    <Zap className="size-5" />
                  </div>
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h1 className="font-display text-3xl font-bold tracking-tight sm:text-4xl">
                        {t('hpxPulse.title')}
                      </h1>
                      <Badge
                        variant="outline"
                        className={cn(
                          'h-7 gap-1.5 rounded-full px-2.5 text-[10px] font-semibold tracking-wide uppercase',
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
                              ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]'
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
                    <p className="text-muted-foreground mt-1.5 max-w-3xl text-sm leading-relaxed">
                      {t('hpxPulse.descriptionMerged', {
                        defaultValue: 'HPX Pulse tunnels plus legacy ICMP (Narnia) — one place for Iran ↔ abroad paths.',
                      })}
                    </p>
                    <p className="text-muted-foreground mt-1 font-mono text-[11px]" dir="ltr">
                      {t('hpxPulse.enginePin', { defaultValue: 'Engine pin' })}: v
                      {engineInfo?.engine_version || '—'}
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="h-10 w-10 rounded-xl p-0"
                  title={t('refresh', { defaultValue: 'Refresh' })}
                  onClick={() => void refetch()}
                  disabled={isFetching}
                >
                  <RefreshCw className={cn('size-3.5', isFetching && 'animate-spin')} />
                </Button>
                {activeTab === 'pulse' && canCreate && (
                  <Button
                    type="button"
                    size="sm"
                    className="h-10 gap-1.5 rounded-xl"
                    onClick={() => window.dispatchEvent(new CustomEvent('openHpxPulseDialog'))}
                  >
                    <Plus className="size-3.5" />
                    {t('hpxPulse.add')}
                  </Button>
                )}
                {activeTab === 'icmp' && canCreateIcmp && (
                  <Button
                    type="button"
                    size="sm"
                    className="h-10 gap-1.5 rounded-xl"
                    onClick={() => window.dispatchEvent(new CustomEvent('openHpxTunnelDialog'))}
                  >
                    <Plus className="size-3.5" />
                    {t('hpxTunnel.addTunnel')}
                  </Button>
                )}
              </div>
            </div>

            {showPulseTab && showIcmpTab && (
              <Tabs
                value={activeTab}
                onValueChange={value => setSearchParams(value === 'icmp' ? { tab: 'icmp' } : {}, { replace: true })}
                className="w-full max-w-md"
              >
                <TabsList className="bg-card/50 grid h-11 w-full grid-cols-2 rounded-2xl border border-white/10 p-1 backdrop-blur-md">
                  <TabsTrigger value="pulse" className="gap-1.5 rounded-xl text-xs data-[state=active]:shadow-md">
                    <Zap className="size-3.5" />
                    {t('hpxPulse.tabPulse', { defaultValue: 'Pulse' })}
                  </TabsTrigger>
                  <TabsTrigger value="icmp" className="gap-1.5 rounded-xl text-xs data-[state=active]:shadow-md">
                    <Radar className="size-3.5" />
                    {t('hpxPulse.tabIcmp', { defaultValue: 'ICMP (legacy)' })}
                  </TabsTrigger>
                </TabsList>
              </Tabs>
            )}

            {activeTab === 'pulse' && showPulseTab && (
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6">
              <Card className="border-white/10 bg-card/50 space-y-3 p-4 xl:col-span-2">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <Gauge className="text-primary size-4" />
                    <span className="text-xs font-semibold tracking-wide uppercase">
                      {t('hpxPulse.fleetHealth', { defaultValue: 'Fleet health' })}
                    </span>
                  </div>
                  <span className="font-mono text-lg font-bold tabular-nums text-emerald-500">
                    {overview.healthPercent}%
                  </span>
                </div>
                <Progress
                  value={overview.healthPercent}
                  className="h-2 rounded-full"
                  indicatorClassName={overview.attention > 0 ? 'bg-amber-500' : 'bg-emerald-500'}
                />
                <p className="text-muted-foreground text-[11px]">
                  {t('hpxPulse.runningOfTotal', {
                    defaultValue: '{{running}} of {{total}} tunnels running',
                    running: overview.running,
                    total: overview.total,
                  })}
                </p>
              </Card>

              <Card className="border-white/10 bg-card/50 flex items-center gap-3 p-4">
                <div className="bg-emerald-500/15 text-emerald-500 flex size-10 items-center justify-center rounded-xl">
                  <Activity className="size-4" />
                </div>
                <div>
                  <p className="font-mono text-2xl font-bold leading-none tabular-nums">{overview.running}</p>
                  <p className="text-muted-foreground mt-1.5 text-[10px] uppercase tracking-wide">
                    {t('hpxPulse.runningLabel', { defaultValue: 'Running' })}
                  </p>
                </div>
              </Card>

              <Card className="border-white/10 bg-card/50 flex items-center gap-3 p-4">
                <div className={cn(
                  'flex size-10 items-center justify-center rounded-xl',
                  overview.attention > 0
                    ? 'bg-amber-500/15 text-amber-500'
                    : 'bg-muted text-muted-foreground',
                )}>
                  <CircleAlert className="size-4" />
                </div>
                <div>
                  <p className="font-mono text-2xl font-bold leading-none tabular-nums">{overview.attention}</p>
                  <p className="text-muted-foreground mt-1.5 text-[10px] uppercase tracking-wide">
                    {t('hpxPulse.attentionLabel', { defaultValue: 'Attention' })}
                  </p>
                </div>
              </Card>

              <Card className="border-white/10 bg-card/50 flex items-center gap-3 p-4">
                <div className="flex size-10 items-center justify-center rounded-xl bg-sky-500/15 text-sky-500">
                  <RadioTower className="size-4" />
                </div>
                <div>
                  <p className="font-mono text-2xl font-bold leading-none tabular-nums" dir="ltr">
                    {overview.connectedAgents}/{overview.expectedAgents}
                  </p>
                  <p className="text-muted-foreground mt-1.5 text-[10px] uppercase tracking-wide">
                    {t('hpxPulse.agentsOnline', { defaultValue: 'Agents online' })}
                  </p>
                </div>
              </Card>

              <Card className="border-white/10 bg-card/50 space-y-2 p-4">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Timer className="size-4 text-teal-400" />
                    <div>
                      <p className="font-mono text-2xl font-bold leading-none tabular-nums">
                        {overview.autoSync}
                      </p>
                      <p className="text-muted-foreground mt-1.5 text-[10px] uppercase tracking-wide">
                        {t('hpxPulse.autoSyncLabel', { defaultValue: 'Auto sync' })}
                      </p>
                    </div>
                  </div>
                  <div className="text-end">
                    <p className="font-mono text-sm font-bold tabular-nums text-emerald-400" dir="ltr">
                      {overview.averagePing != null ? `${overview.averagePing.toFixed(1)} ms` : '—'}
                    </p>
                    <p className="text-muted-foreground mt-1 text-[9px] uppercase tracking-wide">
                      {t('hpxPulse.avgPing', { defaultValue: 'Avg ping' })}
                    </p>
                  </div>
                </div>
              </Card>
            </div>
            )}
          </div>
        </section>
      </PageTransition>
      <PageTransition isContentTransition className="flex min-h-0 flex-1 flex-col">
        {activeTab === 'icmp' && showIcmpTab ? (
          <HpxTunnelsList embedded />
        ) : showPulseTab ? (
          <HpxPulseList />
        ) : null}
      </PageTransition>
    </div>
  )
}
