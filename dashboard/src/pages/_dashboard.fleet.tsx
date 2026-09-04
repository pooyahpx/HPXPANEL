import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
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
import { ExternalLink, KeyRound, Network, Radar, RefreshCw, Server, Zap } from 'lucide-react'
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
  meta?: string | null
  lastSeen?: string | null
}

const formatLastSeen = (value?: string | null) => {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  const year = date.getFullYear()
  if (year < 2005) return '—'
  return date.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
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
    case 'down':
      return 'border-destructive/35 bg-destructive/10 text-destructive'
    default:
      return 'border-border bg-muted/40 text-muted-foreground'
  }
}

const typeMeta = (type: AgentRow['type']) => {
  switch (type) {
    case 'node':
      return { icon: Server, className: 'border-sky-500/30 bg-sky-500/10 text-sky-600 dark:text-sky-400' }
    case 'tunnel':
      return { icon: Radar, className: 'border-violet-500/30 bg-violet-500/10 text-violet-600 dark:text-violet-400' }
    case 'pulse':
      return { icon: Zap, className: 'border-amber-500/30 bg-amber-500/10 text-amber-600 dark:text-amber-400' }
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
      meta: [node.node_version, node.xray_version].filter(Boolean).join(' · ') || null,
      lastSeen: node.last_status_change,
    }))
    const tunnels: AgentRow[] = (data?.tunnels ?? []).map((tunnel: FleetTunnelSummary) => ({
      key: `tunnel-${tunnel.id}`,
      type: 'tunnel',
      id: tunnel.id,
      name: tunnel.name,
      status: tunnel.status,
      host: tunnel.agent_host,
      meta: tunnel.agent_claimed
        ? t('fleet.agentClaimed', { defaultValue: 'Agent claimed' })
        : t('fleet.agentPending', { defaultValue: 'Waiting for agent' }),
      lastSeen: tunnel.agent_last_seen,
    }))
    const pulses: AgentRow[] = (data?.pulses ?? []).map((pulse: FleetPulseSummary) => ({
      key: `pulse-${pulse.id}`,
      type: 'pulse',
      id: pulse.id,
      name: pulse.name,
      status: pulse.status,
      host: [pulse.iran_agent_host, pulse.abroad_agent_host].filter(Boolean).join(' · ') || null,
      meta: t('fleet.pulseAgents', {
        defaultValue: 'Iran {{iran}} · Abroad {{abroad}}',
        iran: pulse.iran_claimed
          ? t('fleet.claimed', { defaultValue: 'claimed' })
          : t('fleet.pending', { defaultValue: 'pending' }),
        abroad: pulse.abroad_claimed
          ? t('fleet.claimed', { defaultValue: 'claimed' })
          : t('fleet.pending', { defaultValue: 'pending' }),
      }),
      lastSeen: pulse.iran_agent_last_seen || pulse.abroad_agent_last_seen,
    }))
    return [...nodes, ...tunnels, ...pulses]
  }, [data, t])

  const regenerateTunnel = async (id: number) => {
    try {
      const result = await tunnelTokenMutation.mutateAsync(id)
      toast.success(t('fleet.regenerateSuccess', { defaultValue: 'Join token regenerated' }), {
        description: result.join_command || result.join_token,
      })
    } catch (error: any) {
      toast.error(t('fleet.regenerateFailed', { defaultValue: 'Could not regenerate join token' }), {
        description: error?.data?.detail || error?.message,
      })
    }
  }

  const regeneratePulse = async (id: number) => {
    try {
      const result: any = await pulseTokenMutation.mutateAsync(id)
      toast.success(t('fleet.regenerateSuccess', { defaultValue: 'Join token regenerated' }), {
        description: result?.iran_join_command || result?.abroad_join_command || result?.message,
      })
    } catch (error: any) {
      toast.error(t('fleet.regenerateFailed', { defaultValue: 'Could not regenerate join token' }), {
        description: error?.data?.detail || error?.message,
      })
    }
  }

  const typeLabel = (type: AgentRow['type']) => {
    if (type === 'node') return t('fleet.typeNode', { defaultValue: 'Node' })
    if (type === 'tunnel') return t('fleet.typeTunnel', { defaultValue: 'Tunnel' })
    return t('fleet.typePulse', { defaultValue: 'Pulse' })
  }

  if (!canView) {
    return (
      <div className="p-6">
        <p className="text-muted-foreground text-sm">{t('error', { defaultValue: 'Permission denied' })}</p>
      </div>
    )
  }

  return (
    <div className="flex min-h-0 w-full flex-1 flex-col items-start gap-0">
      <PageTransition isContentTransition className="w-full">
        <section dir={dir} className="relative w-full overflow-hidden border-b px-4 py-5 md:px-6 md:py-6">
          <div className="bg-primary/5 pointer-events-none absolute end-0 top-0 size-48 translate-x-1/3 -translate-y-1/2 rounded-full blur-3xl" />
          <div className="relative flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0 space-y-2">
              <div className="flex items-center gap-2">
                <div className="bg-primary/10 text-primary flex size-9 items-center justify-center border border-primary/20">
                  <Network className="size-4" />
                </div>
                <div>
                  <h1 className="font-display text-2xl font-bold tracking-tight sm:text-3xl">
                    {t('fleet.title', { defaultValue: 'Fleet' })}
                  </h1>
                  <p className="text-muted-foreground text-sm">
                    {t('fleet.subtitle', { defaultValue: 'Unified view of edge nodes, HPX tunnels, and Pulse agents' })}
                  </p>
                </div>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <div className="bg-background/70 flex overflow-hidden border">
                {[
                  { label: t('fleet.typeNode', { defaultValue: 'Node' }), value: data?.totals.nodes ?? 0 },
                  { label: t('fleet.typeTunnel', { defaultValue: 'Tunnel' }), value: data?.totals.tunnels ?? 0 },
                  { label: t('fleet.typePulse', { defaultValue: 'Pulse' }), value: data?.totals.pulses ?? 0 },
                ].map((stat, index) => (
                  <div
                    key={stat.label}
                    className={cn('min-w-[4.5rem] px-3 py-2', index < 2 && 'border-e')}
                  >
                    <p className="text-muted-foreground text-[10px] font-medium tracking-wide">{stat.label}</p>
                    <p className="mt-0.5 font-mono text-lg font-semibold tabular-nums">{stat.value}</p>
                  </div>
                ))}
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
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, index) => (
                <Skeleton key={index} className="h-14 w-full rounded-none" />
              ))}
            </div>
          )}

          {isError && (
            <Card className="rounded-none">
              <CardContent className="text-muted-foreground p-4 text-sm">
                {t('fleet.loadError', { defaultValue: 'Could not load fleet summary' })}
              </CardContent>
            </Card>
          )}

          {!isLoading && !isError && rows.length === 0 && (
            <Card className="rounded-none">
              <CardContent className="text-muted-foreground p-6 text-sm">
                {t('fleet.empty', { defaultValue: 'No nodes, tunnels, or pulses yet' })}
              </CardContent>
            </Card>
          )}

          {!isLoading && !isError && rows.length > 0 && (
            <>
              {/* Mobile cards */}
              <div className="grid gap-3 md:hidden">
                {rows.map(row => {
                  const meta = typeMeta(row.type)
                  const Icon = meta.icon
                  return (
                    <Card key={row.key} className="rounded-none">
                      <CardContent className="space-y-3 p-4">
                        <div className="flex items-start justify-between gap-3">
                          <div className="min-w-0 space-y-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <Badge variant="outline" className={cn('h-6 gap-1 rounded-none text-[10px]', meta.className)}>
                                <Icon className="size-3" />
                                {typeLabel(row.type)}
                              </Badge>
                              <Badge variant="outline" className={cn('h-6 rounded-none text-[10px] uppercase', statusTone(row.status))}>
                                {row.status}
                              </Badge>
                            </div>
                            <p className="truncate text-base font-semibold">{row.name}</p>
                            {row.meta && <p className="text-muted-foreground truncate text-xs">{row.meta}</p>}
                          </div>
                        </div>
                        <div className="text-muted-foreground grid grid-cols-2 gap-2 text-xs">
                          <div>
                            <p className="mb-0.5 opacity-70">{t('fleet.colHost', { defaultValue: 'Host' })}</p>
                            <p className="truncate font-mono">{row.host || '—'}</p>
                          </div>
                          <div>
                            <p className="mb-0.5 opacity-70">{t('fleet.colLastSeen', { defaultValue: 'Last seen' })}</p>
                            <p className="truncate font-mono">{formatLastSeen(row.lastSeen)}</p>
                          </div>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {row.type === 'node' && (
                            <Button asChild variant="outline" size="sm" className="h-8 rounded-none">
                              <Link to="/nodes">
                                <ExternalLink className="size-3.5" />
                                {t('fleet.openNodes', { defaultValue: 'Nodes' })}
                              </Link>
                            </Button>
                          )}
                          {row.type === 'tunnel' && (
                            <>
                              <Button asChild variant="outline" size="sm" className="h-8 rounded-none">
                                <Link to="/hpx-tunnel">
                                  <ExternalLink className="size-3.5" />
                                  {t('fleet.openTunnel', { defaultValue: 'Tunnel' })}
                                </Link>
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
                                  {t('fleet.regenerateToken', { defaultValue: 'Join token' })}
                                </Button>
                              )}
                            </>
                          )}
                          {row.type === 'pulse' && (
                            <>
                              <Button asChild variant="outline" size="sm" className="h-8 rounded-none">
                                <Link to="/hpx-pulse">
                                  <ExternalLink className="size-3.5" />
                                  {t('fleet.openPulse', { defaultValue: 'Pulse' })}
                                </Link>
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
                                  {t('fleet.regenerateToken', { defaultValue: 'Join token' })}
                                </Button>
                              )}
                            </>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  )
                })}
              </div>

              {/* Desktop table */}
              <div className="hidden overflow-hidden border md:block">
                <Table>
                  <TableHeader>
                    <TableRow className="bg-muted/30 hover:bg-muted/30">
                      <TableHead className="w-[7.5rem]">{t('fleet.colType', { defaultValue: 'Type' })}</TableHead>
                      <TableHead className="min-w-[12rem]">{t('fleet.colName', { defaultValue: 'Name' })}</TableHead>
                      <TableHead className="w-[8rem]">{t('fleet.colStatus', { defaultValue: 'Status' })}</TableHead>
                      <TableHead className="min-w-[10rem]">{t('fleet.colHost', { defaultValue: 'Host' })}</TableHead>
                      <TableHead className="w-[9rem]">{t('fleet.colLastSeen', { defaultValue: 'Last seen' })}</TableHead>
                      <TableHead className="w-[7rem] text-end">{t('fleet.colActions', { defaultValue: 'Actions' })}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {rows.map(row => {
                      const meta = typeMeta(row.type)
                      const Icon = meta.icon
                      return (
                        <TableRow key={row.key}>
                          <TableCell>
                            <Badge variant="outline" className={cn('h-6 gap-1 rounded-none text-[10px]', meta.className)}>
                              <Icon className="size-3 shrink-0" />
                              <span className="whitespace-nowrap">{typeLabel(row.type)}</span>
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <div className="min-w-0 space-y-0.5">
                              <p className="truncate font-medium">{row.name}</p>
                              {row.meta && <p className="text-muted-foreground truncate font-mono text-[11px]">{row.meta}</p>}
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline" className={cn('h-6 rounded-none text-[10px] uppercase', statusTone(row.status))}>
                              {row.status}
                            </Badge>
                          </TableCell>
                          <TableCell>
                            <p className="text-muted-foreground max-w-[16rem] truncate font-mono text-xs">{row.host || '—'}</p>
                          </TableCell>
                          <TableCell>
                            <p className="text-muted-foreground whitespace-nowrap font-mono text-xs">{formatLastSeen(row.lastSeen)}</p>
                          </TableCell>
                          <TableCell>
                            <div className="flex items-center justify-end gap-1">
                              {row.type === 'node' && (
                                <Button asChild variant="ghost" size="icon" className="size-8 rounded-none" title={t('fleet.openNodes', { defaultValue: 'Nodes' })}>
                                  <Link to="/nodes">
                                    <ExternalLink className="size-4" />
                                  </Link>
                                </Button>
                              )}
                              {row.type === 'tunnel' && (
                                <>
                                  <Button asChild variant="ghost" size="icon" className="size-8 rounded-none" title={t('fleet.openTunnel', { defaultValue: 'Tunnel' })}>
                                    <Link to="/hpx-tunnel">
                                      <ExternalLink className="size-4" />
                                    </Link>
                                  </Button>
                                  {canUpdateTunnel && (
                                    <Button
                                      variant="ghost"
                                      size="icon"
                                      className="size-8 rounded-none"
                                      title={t('fleet.regenerateToken', { defaultValue: 'Join token' })}
                                      disabled={tunnelTokenMutation.isPending}
                                      onClick={() => regenerateTunnel(row.id)}
                                    >
                                      <KeyRound className="size-4" />
                                    </Button>
                                  )}
                                </>
                              )}
                              {row.type === 'pulse' && (
                                <>
                                  <Button asChild variant="ghost" size="icon" className="size-8 rounded-none" title={t('fleet.openPulse', { defaultValue: 'Pulse' })}>
                                    <Link to="/hpx-pulse">
                                      <ExternalLink className="size-4" />
                                    </Link>
                                  </Button>
                                  {canUpdatePulse && (
                                    <Button
                                      variant="ghost"
                                      size="icon"
                                      className="size-8 rounded-none"
                                      title={t('fleet.regenerateToken', { defaultValue: 'Join token' })}
                                      disabled={pulseTokenMutation.isPending}
                                      onClick={() => regeneratePulse(row.id)}
                                    >
                                      <KeyRound className="size-4" />
                                    </Button>
                                  )}
                                </>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              </div>
            </>
          )}
        </main>
      </PageTransition>
    </div>
  )
}
