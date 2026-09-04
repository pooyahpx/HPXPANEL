import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import PageTransition from '@/components/layout/page-transition'
import { useAdmin } from '@/hooks/use-admin'
import useDirDetection from '@/hooks/use-dir-detection'
import { cn } from '@/lib/utils'
import {
  FleetNodeSummary,
  FleetPulseSummary,
  FleetTunnelSummary,
  useFleetSummary,
  useRegenerateFleetPulseTokens,
  useRegenerateFleetTunnelToken,
} from '@/service/api/fleet'
import { canReadResourcePage, hasPermission } from '@/utils/rbac'
import { KeyRound, Network, Radar, RefreshCw, Server, Zap } from 'lucide-react'
import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'
import { toast } from 'sonner'

type AgentRow = {
  key: string
  type: 'node' | 'tunnel' | 'pulse'
  id: number
  name: string
  status: string
  host?: string | null
  version?: string | null
  lastSeen?: string | null
  detail?: string | null
}

const formatLastSeen = (value?: string | null) => {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString()
}

const statusTone = (status: string) => {
  switch (status) {
    case 'connected':
    case 'running':
      return 'border-emerald-500/35 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
    case 'connecting':
    case 'partial':
    case 'starting':
      return 'border-amber-500/35 bg-amber-500/10 text-amber-600 dark:text-amber-400'
    case 'error':
    case 'unhealthy':
    case 'disabled':
      return 'border-destructive/35 bg-destructive/10 text-destructive'
    default:
      return 'border-border bg-muted/40 text-muted-foreground'
  }
}

const typeBadge = (type: AgentRow['type'], t: (key: string) => string) => {
  switch (type) {
    case 'node':
      return { label: t('fleet.typeNode'), icon: Server }
    case 'tunnel':
      return { label: t('fleet.typeTunnel'), icon: Radar }
    case 'pulse':
      return { label: t('fleet.typePulse'), icon: Zap }
  }
}

export default function FleetPage() {
  const { t } = useTranslation()
  const dir = useDirDetection()
  const { admin } = useAdmin()
  const canView = canReadResourcePage(admin, 'nodes') || hasPermission(admin, 'system', 'read')
  const canUpdateTunnel = hasPermission(admin, 'hpx_tunnels', 'update')
  const canUpdatePulse = hasPermission(admin, 'hpx_pulse', 'update')

  const { data, isLoading, isError, isFetching, refetch } = useFleetSummary({
    enabled: canView,
    refetchInterval: canView ? 15_000 : false,
  })
  const tunnelTokenMutation = useRegenerateFleetTunnelToken()
  const pulseTokenMutation = useRegenerateFleetPulseTokens()

  const rows = useMemo<AgentRow[]>(() => {
    const nodes: AgentRow[] = (data?.nodes ?? []).map((node: FleetNodeSummary) => ({
      key: `node-${node.id}`,
      type: 'node',
      id: node.id,
      name: node.name,
      status: node.status,
      host: node.address,
      version: [node.node_version, node.xray_version].filter(Boolean).join(' / ') || null,
      lastSeen: node.last_status_change,
    }))
    const tunnels: AgentRow[] = (data?.tunnels ?? []).map((tunnel: FleetTunnelSummary) => ({
      key: `tunnel-${tunnel.id}`,
      type: 'tunnel',
      id: tunnel.id,
      name: tunnel.name,
      status: tunnel.status,
      host: tunnel.agent_host,
      version: tunnel.agent_claimed ? t('fleet.agentClaimed') : t('fleet.agentPending'),
      lastSeen: tunnel.agent_last_seen,
    }))
    const pulses: AgentRow[] = (data?.pulses ?? []).map((pulse: FleetPulseSummary) => ({
      key: `pulse-${pulse.id}`,
      type: 'pulse',
      id: pulse.id,
      name: pulse.name,
      status: pulse.status,
      host: [pulse.iran_agent_host, pulse.abroad_agent_host].filter(Boolean).join(' · ') || null,
      version: t('fleet.pulseAgents', {
        iran: pulse.iran_claimed ? t('fleet.claimed') : t('fleet.pending'),
        abroad: pulse.abroad_claimed ? t('fleet.claimed') : t('fleet.pending'),
      }),
      lastSeen: pulse.iran_agent_last_seen || pulse.abroad_agent_last_seen,
      detail: [
        pulse.iran_agent_last_seen ? `IR ${formatLastSeen(pulse.iran_agent_last_seen)}` : null,
        pulse.abroad_agent_last_seen ? `AB ${formatLastSeen(pulse.abroad_agent_last_seen)}` : null,
      ]
        .filter(Boolean)
        .join(' · '),
    }))
    return [...nodes, ...tunnels, ...pulses]
  }, [data, t])

  const regenerateTunnel = async (id: number) => {
    try {
      const result = await tunnelTokenMutation.mutateAsync(id)
      toast.success(t('fleet.regenerateSuccess'), {
        description: result.join_command || result.join_token,
      })
    } catch (error: any) {
      toast.error(t('fleet.regenerateFailed'), {
        description: error?.data?.detail || error?.message,
      })
    }
  }

  const regeneratePulse = async (id: number) => {
    try {
      const result: any = await pulseTokenMutation.mutateAsync(id)
      toast.success(t('fleet.regenerateSuccess'), {
        description: result?.iran_join_command || result?.abroad_join_command || result?.message,
      })
    } catch (error: any) {
      toast.error(t('fleet.regenerateFailed'), {
        description: error?.data?.detail || error?.message,
      })
    }
  }

  if (!canView) {
    return (
      <div className="p-6">
        <p className="text-muted-foreground text-sm">{t('error')}</p>
      </div>
    )
  }

  return (
    <div className="flex min-h-0 w-full flex-1 flex-col items-start gap-0">
      <PageTransition isContentTransition className="w-full">
        <section dir={dir} className="relative w-full overflow-hidden border-b px-4 py-5 md:px-6 md:py-6">
          <div className="relative flex flex-wrap items-end justify-between gap-4">
            <div className="border-primary max-w-3xl space-y-2 border-s-2 ps-4">
              <div className="text-primary flex items-center gap-2 font-mono text-[10px] font-bold tracking-[0.18em] uppercase">
                <Network className="h-3.5 w-3.5" aria-hidden="true" />
                HPXPANEL / {t('fleet.title')}
              </div>
              <h1 className="font-display text-3xl leading-none font-black tracking-[-0.04em] uppercase sm:text-4xl">
                {t('fleet.title')}
              </h1>
              <p className="text-muted-foreground max-w-2xl text-xs leading-relaxed sm:text-sm">{t('fleet.subtitle')}</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <div className="grid grid-cols-3 border">
                <div className="border-border min-w-20 border-e px-3 py-2">
                  <p className="text-muted-foreground font-mono text-[8px] font-bold tracking-[0.14em] uppercase">{t('fleet.typeNode')}</p>
                  <p className="mt-1 font-mono text-lg font-bold tabular-nums">{data?.totals.nodes ?? 0}</p>
                </div>
                <div className="border-border min-w-20 border-e px-3 py-2">
                  <p className="text-muted-foreground font-mono text-[8px] font-bold tracking-[0.14em] uppercase">{t('fleet.typeTunnel')}</p>
                  <p className="mt-1 font-mono text-lg font-bold tabular-nums">{data?.totals.tunnels ?? 0}</p>
                </div>
                <div className="min-w-20 px-3 py-2">
                  <p className="text-muted-foreground font-mono text-[8px] font-bold tracking-[0.14em] uppercase">{t('fleet.typePulse')}</p>
                  <p className="mt-1 font-mono text-lg font-bold tabular-nums">{data?.totals.pulses ?? 0}</p>
                </div>
              </div>
              <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
                <RefreshCw className={cn('size-4', isFetching && 'animate-spin')} />
                {t('refresh', { defaultValue: 'Refresh' })}
              </Button>
            </div>
          </div>
        </section>

        <main className="mx-auto w-full max-w-[1800px] space-y-4 px-3 py-4 sm:px-4 md:px-6 md:py-6">
          {isLoading && (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {Array.from({ length: 6 }).map((_, index) => (
                <Skeleton key={index} className="h-36 w-full rounded-none" />
              ))}
            </div>
          )}

          {isError && (
            <Card className="rounded-none">
              <CardContent className="text-muted-foreground p-4 text-sm">{t('fleet.loadError')}</CardContent>
            </Card>
          )}

          {!isLoading && !isError && rows.length === 0 && (
            <Card className="rounded-none">
              <CardContent className="text-muted-foreground p-6 text-sm">{t('fleet.empty')}</CardContent>
            </Card>
          )}

          {!isLoading && !isError && rows.length > 0 && (
            <div className="overflow-hidden border">
              <div className="bg-muted/30 text-muted-foreground hidden grid-cols-[7rem_minmax(0,1.4fr)_7rem_minmax(0,1fr)_minmax(0,1fr)_8rem] gap-3 border-b px-4 py-2 font-mono text-[10px] font-bold tracking-[0.12em] uppercase md:grid">
                <span>{t('fleet.colType')}</span>
                <span>{t('fleet.colName')}</span>
                <span>{t('fleet.colStatus')}</span>
                <span>{t('fleet.colHost')}</span>
                <span>{t('fleet.colLastSeen')}</span>
                <span>{t('fleet.colActions')}</span>
              </div>
              <ul className="divide-border divide-y">
                {rows.map(row => {
                  const badge = typeBadge(row.type, t)
                  const Icon = badge.icon
                  return (
                    <li
                      key={row.key}
                      className="grid gap-3 px-4 py-3 md:grid-cols-[7rem_minmax(0,1.4fr)_7rem_minmax(0,1fr)_minmax(0,1fr)_8rem] md:items-center"
                    >
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="h-6 gap-1 rounded-none text-[10px] uppercase">
                          <Icon className="size-3" />
                          {badge.label}
                        </Badge>
                      </div>
                      <div className="min-w-0">
                        <p className="truncate font-medium">{row.name}</p>
                        {row.version && <p className="text-muted-foreground truncate font-mono text-[11px]">{row.version}</p>}
                        {row.detail && <p className="text-muted-foreground truncate text-[11px] md:hidden">{row.detail}</p>}
                      </div>
                      <div>
                        <Badge variant="outline" className={cn('h-6 rounded-none text-[10px] uppercase', statusTone(row.status))}>
                          {row.status}
                        </Badge>
                      </div>
                      <p className="text-muted-foreground truncate font-mono text-xs">{row.host || '—'}</p>
                      <p className="text-muted-foreground truncate font-mono text-xs">{formatLastSeen(row.lastSeen)}</p>
                      <div className="flex flex-wrap gap-2">
                        {row.type === 'node' && (
                          <Button asChild variant="outline" size="sm" className="h-8 rounded-none">
                            <Link to="/nodes">{t('fleet.openNodes')}</Link>
                          </Button>
                        )}
                        {row.type === 'tunnel' && (
                          <>
                            <Button asChild variant="outline" size="sm" className="h-8 rounded-none">
                              <Link to="/hpx-tunnel">{t('fleet.openTunnel')}</Link>
                            </Button>
                            {canUpdateTunnel && (
                              <Button
                                variant="outline"
                                size="sm"
                                className="h-8 rounded-none"
                                disabled={tunnelTokenMutation.isPending}
                                onClick={() => regenerateTunnel(row.id)}
                              >
                                <KeyRound className="size-3.5" />
                                {t('fleet.regenerateToken')}
                              </Button>
                            )}
                          </>
                        )}
                        {row.type === 'pulse' && (
                          <>
                            <Button asChild variant="outline" size="sm" className="h-8 rounded-none">
                              <Link to="/hpx-pulse">{t('fleet.openPulse')}</Link>
                            </Button>
                            {canUpdatePulse && (
                              <Button
                                variant="outline"
                                size="sm"
                                className="h-8 rounded-none"
                                disabled={pulseTokenMutation.isPending}
                                onClick={() => regeneratePulse(row.id)}
                              >
                                <KeyRound className="size-3.5" />
                                {t('fleet.regenerateToken')}
                              </Button>
                            )}
                          </>
                        )}
                      </div>
                    </li>
                  )
                })}
              </ul>
            </div>
          )}
        </main>
      </PageTransition>
    </div>
  )
}
