import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { ChartContainer, ChartTooltip, ChartTooltipContent } from '@/components/ui/chart'
import useDirDetection from '@/hooks/use-dir-detection'
import { useAdmin } from '@/hooks/use-admin'
import { cn } from '@/lib/utils'
import { ProtocolHealthStatus, useObservabilityHistory, useObservabilitySummary } from '@/service/api/observability'
import { hasPermission } from '@/utils/rbac'
import { Activity, AlertTriangle, Cpu, HardDrive, Network, Server, Users } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { CartesianGrid, Line, LineChart, XAxis, YAxis } from 'recharts'

const statusColor: Record<ProtocolHealthStatus, string> = {
  healthy: 'bg-green-500',
  degraded: 'bg-amber-500',
  down: 'bg-destructive',
  unknown: 'bg-muted-foreground',
}

const nodeStatusDot = (status: string) => {
  switch (status) {
    case 'connected':
      return 'bg-green-500'
    case 'connecting':
      return 'bg-amber-500'
    case 'error':
      return 'bg-destructive'
    default:
      return 'bg-muted-foreground'
  }
}

const formatUptime = (seconds?: number | null) => {
  if (!seconds) return '—'
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  if (days > 0) return `${days}d ${hours}h`
  const mins = Math.floor((seconds % 3600) / 60)
  return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`
}

const ObservabilityPage = () => {
  const { t } = useTranslation()
  const dir = useDirDetection()
  const { admin } = useAdmin()
  const canView = hasPermission(admin, 'nodes', 'stats')
  const [historyScope, setHistoryScope] = useState<'master' | number>('master')

  const { data, isLoading, isError } = useObservabilitySummary({
    enabled: canView,
    // A summary probes every node; avoid overlapping the node agent's
    // one-second CPU samples on larger fleets.
    refetchInterval: canView ? 10_000 : false,
  })

  const { data: history } = useObservabilityHistory(
    {
      node_id: historyScope === 'master' ? undefined : historyScope,
      hours: 24,
    },
    { enabled: canView && Boolean(data?.node_stats_recording_enabled) },
  )

  const connectedNodes = useMemo(() => data?.nodes.filter(node => node.status === 'connected').length ?? 0, [data?.nodes])
  const chartData = useMemo(
    () =>
      (history?.stats ?? []).map(point => ({
        label: new Date(point.period_start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        cpu: point.cpu_usage_percentage,
        mem: point.mem_usage_percentage,
      })),
    [history?.stats],
  )

  if (!canView) {
    return (
      <div className="p-6">
        <p className="text-muted-foreground text-sm">{t('error')}</p>
      </div>
    )
  }

  return (
    <div dir={dir} className="w-full">
      <header className="mission-brief relative overflow-hidden border-b">
        <div className="relative z-10 mx-auto flex w-full max-w-[1800px] flex-col gap-5 px-4 py-6 md:px-6 md:py-8 lg:flex-row lg:items-end lg:justify-between">
          <div className="border-primary max-w-3xl border-s-2 ps-4">
            <div className="text-primary mb-2 flex items-center gap-2 font-mono text-[10px] font-bold tracking-[0.18em] uppercase">
              <Activity className="h-3.5 w-3.5" aria-hidden="true" />
              HPXPANEL / {t('observability.title')}
            </div>
            <h1 className="font-display text-3xl leading-none font-black tracking-[-0.04em] uppercase sm:text-4xl">{t('observability.title')}</h1>
            <p className="text-muted-foreground mt-2 max-w-2xl text-xs leading-relaxed sm:text-sm">{t('observability.subtitle')}</p>
          </div>
          <div className="grid grid-cols-3 border">
            <div className="border-border min-w-24 border-e px-3 py-2.5">
              <p className="text-muted-foreground font-mono text-[8px] font-bold tracking-[0.14em] uppercase">{t('nodes.title')}</p>
              <p className="mt-1 font-mono text-lg font-bold tabular-nums">{data?.nodes.length ?? 0}</p>
            </div>
            <div className="border-border min-w-24 border-e px-3 py-2.5">
              <p className="text-muted-foreground font-mono text-[8px] font-bold tracking-[0.14em] uppercase">{t('observability.online')}</p>
              <p className="text-primary mt-1 font-mono text-lg font-bold tabular-nums">{connectedNodes}</p>
            </div>
            <div className="min-w-24 px-3 py-2.5">
              <p className="text-muted-foreground font-mono text-[8px] font-bold tracking-[0.14em] uppercase">{t('observability.recording')}</p>
              <p className="mt-1 font-mono text-xs font-bold uppercase">{data?.node_stats_recording_enabled ? 'ON' : 'OFF'}</p>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-[1800px] space-y-6 px-3 py-4 sm:px-4 md:px-6 md:py-6">
        {isLoading && (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 6 }).map((_, index) => (
              <Skeleton key={index} className="h-48 w-full rounded-none" />
            ))}
          </div>
        )}

        {isError && <p className="text-destructive text-sm">{t('error')}</p>}

        {data?.master && (
          <section aria-label={t('master')}>
            <h2 className="mb-3 font-mono text-xs font-bold tracking-[0.14em] uppercase">{t('master')}</h2>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <Card className="rounded-none">
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-sm">
                    <Cpu className="h-4 w-4" /> CPU
                  </CardTitle>
                </CardHeader>
                <CardContent className="font-mono text-2xl font-bold">{data.master.resources.cpu_usage.toFixed(1)}%</CardContent>
              </Card>
              <Card className="rounded-none">
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-sm">
                    <HardDrive className="h-4 w-4" /> RAM
                  </CardTitle>
                </CardHeader>
                <CardContent className="font-mono text-2xl font-bold">
                  {((data.master.resources.mem_used / data.master.resources.mem_total) * 100).toFixed(1)}%
                </CardContent>
              </Card>
              <Card className="rounded-none">
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-sm">
                    <Users className="h-4 w-4" /> {t('observability.usersOnline')}
                  </CardTitle>
                </CardHeader>
                <CardContent className="font-mono text-2xl font-bold">{data.master.users.online_users}</CardContent>
              </Card>
              <Card className="rounded-none">
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-sm">
                    <Server className="h-4 w-4" /> {t('observability.workers')}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-1 text-xs">
                  <p>
                    Scheduler: <Badge variant="outline">{data.workers?.scheduler.status ?? '—'}</Badge>
                  </p>
                  <p>
                    Node: <Badge variant="outline">{data.workers?.node.status ?? '—'}</Badge>
                  </p>
                </CardContent>
              </Card>
            </div>
          </section>
        )}

        <section aria-label={t('nodes.title')}>
          <h2 className="mb-3 font-mono text-xs font-bold tracking-[0.14em] uppercase">{t('observability.nodeCommandCenter')}</h2>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {data?.nodes.map(node => (
              <Card
                key={node.node_id}
                className={cn('cursor-pointer rounded-none transition-colors', historyScope === node.node_id && 'ring-primary ring-2')}
                onClick={() => setHistoryScope(node.node_id)}
              >
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center justify-between gap-2 text-sm">
                    <span className="flex min-w-0 items-center gap-2">
                      <span className={cn('h-2 w-2 shrink-0 rounded-full', nodeStatusDot(node.status))} />
                      <span className="truncate">{node.name}</span>
                    </span>
                    <span className="text-muted-foreground font-mono text-[10px]">{node.address}</span>
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-xs">
                  <div className="grid grid-cols-2 gap-2 font-mono">
                    <div>CPU: {node.cpu_usage?.toFixed(1) ?? '—'}%</div>
                    <div>RAM: {node.mem_usage_percent?.toFixed(1) ?? '—'}%</div>
                    <div className="flex items-center gap-1">
                      <Network className="h-3 w-3" />↓ {node.incoming_mbps ?? '—'} Mbps
                    </div>
                    <div className="flex items-center gap-1">
                      <Network className="h-3 w-3" />↑ {node.outgoing_mbps ?? '—'} Mbps
                    </div>
                    <div>
                      {t('observability.usersOnline')}: {node.users_online}
                    </div>
                    <div>
                      {t('observability.uptime')}: {formatUptime(node.uptime_seconds)}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {node.protocols.map(protocol => (
                      <Badge key={protocol.protocol} variant="secondary" className="rounded-none font-mono text-[10px]">
                        <span className={cn('me-1 inline-block h-1.5 w-1.5 rounded-full', statusColor[protocol.status])} />
                        {protocol.protocol}
                        {protocol.latency_ms ? ` ${protocol.latency_ms}ms` : ''}
                      </Badge>
                    ))}
                  </div>
                  {(node.latency_ms || node.packet_loss_percent) && (
                    <p className="text-muted-foreground font-mono text-[10px]">
                      {node.latency_ms ? `Latency ${node.latency_ms}ms` : ''}
                      {node.packet_loss_percent ? ` · Loss ${node.packet_loss_percent}%` : ''}
                    </p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        {data?.node_stats_recording_enabled && chartData.length > 0 && (
          <section>
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <h2 className="font-mono text-xs font-bold tracking-[0.14em] uppercase">{t('observability.history24h')}</h2>
              <button type="button" className="text-primary font-mono text-[10px] uppercase" onClick={() => setHistoryScope('master')}>
                {t('master')}
              </button>
            </div>
            <Card className="rounded-none">
              <CardContent className="pt-6">
                <ChartContainer
                  config={{
                    cpu: { label: 'CPU %', color: 'hsl(var(--chart-1))' },
                    mem: { label: 'RAM %', color: 'hsl(var(--chart-2))' },
                  }}
                  className="h-[280px] w-full"
                >
                  <LineChart data={chartData}>
                    <CartesianGrid vertical={false} />
                    <XAxis dataKey="label" tickLine={false} axisLine={false} fontSize={10} />
                    <YAxis domain={[0, 100]} tickLine={false} axisLine={false} fontSize={10} />
                    <ChartTooltip content={<ChartTooltipContent />} />
                    <Line type="monotone" dataKey="cpu" stroke="var(--color-cpu)" dot={false} strokeWidth={2} />
                    <Line type="monotone" dataKey="mem" stroke="var(--color-mem)" dot={false} strokeWidth={2} />
                  </LineChart>
                </ChartContainer>
              </CardContent>
            </Card>
          </section>
        )}

        {data?.recent_alerts && data.recent_alerts.length > 0 && (
          <section>
            <h2 className="mb-3 flex items-center gap-2 font-mono text-xs font-bold tracking-[0.14em] uppercase">
              <AlertTriangle className="h-4 w-4" />
              {t('observability.recentAlerts')}
            </h2>
            <div className="command-surface divide-y">
              {data.recent_alerts.map(alert => (
                <div key={alert.id} className="flex flex-wrap items-center justify-between gap-2 px-4 py-3 text-xs">
                  <div>
                    <p className="font-medium">{alert.message}</p>
                    <p className="text-muted-foreground font-mono text-[10px]">
                      {alert.scope}
                      {alert.node_name ? ` · ${alert.node_name}` : ''} · {alert.metric} = {alert.value.toFixed(1)}
                    </p>
                  </div>
                  <time className="text-muted-foreground font-mono text-[10px]">{new Date(alert.created_at).toLocaleString()}</time>
                </div>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  )
}

export default ObservabilityPage
