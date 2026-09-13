import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import useDirDetection from '@/hooks/use-dir-detection'
import { cn } from '@/lib/utils'
import {
  NodeRealtimeStats,
  NodeResponse,
  NodeStatus,
  SystemResourceStats,
  SystemUsersStats,
  useGetNodes,
  useRealtimeNodesStats,
} from '@/service/api'
import { formatBytes } from '@/utils/formatByte'
import { displayCountryName, resolveInfraLocation, resolveLocationFromTimezone, type InfraLocation } from '@/utils/infra-location'
import { useResolvedInfraLocations } from '@/hooks/use-resolved-infra-locations'
import { Box, Building2, Cpu, Globe, HardDrive, MapPin, MemoryStick, Network, Server, Shield, Zap } from 'lucide-react'
import { useMemo, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

type ServerTopologyCardProps = {
  resourceData?: SystemResourceStats
  usersData?: SystemUsersStats
  canReadNodes?: boolean
  canReadNodeStats?: boolean
}

type OsBrand = {
  letter: string
  label: string
  from: string
  to: string
  ring: string
}

const formatCompactUptime = (seconds?: number | null) => {
  const total = Math.max(0, Math.floor(Number(seconds) || 0))
  const days = Math.floor(total / 86400)
  const hours = Math.floor((total % 86400) / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const secs = total % 60
  if (days > 0) return `${days}d ${hours}h ${minutes}m`
  if (hours > 0) return `${hours}h ${minutes}m ${secs}s`
  if (minutes > 0) return `${minutes}m ${secs}s`
  return `${secs}s`
}

const resolveOsBrand = (osName?: string | null): OsBrand => {
  const name = (osName || '').toLowerCase()
  if (name.includes('ubuntu')) return { letter: 'U', label: 'Ubuntu', from: '#E95420', to: '#C7460F', ring: 'ring-[#E95420]/40' }
  if (name.includes('debian')) return { letter: 'D', label: 'Debian', from: '#A80030', to: '#7A0023', ring: 'ring-[#A80030]/40' }
  if (name.includes('centos') || name.includes('rocky') || name.includes('alma'))
    return { letter: 'C', label: osName || 'CentOS', from: '#262577', to: '#1A1A55', ring: 'ring-[#262577]/40' }
  if (name.includes('fedora')) return { letter: 'F', label: 'Fedora', from: '#51A2DA', to: '#294172', ring: 'ring-[#51A2DA]/40' }
  if (name.includes('arch')) return { letter: 'A', label: 'Arch', from: '#1793D1', to: '#0C5A82', ring: 'ring-[#1793D1]/40' }
  if (name.includes('windows')) return { letter: 'W', label: 'Windows', from: '#00A4EF', to: '#0078D4', ring: 'ring-[#00A4EF]/40' }
  if (name.includes('darwin') || name.includes('mac')) return { letter: 'M', label: 'macOS', from: '#555555', to: '#222222', ring: 'ring-white/20' }
  return { letter: 'P', label: osName || 'Panel', from: 'hsl(var(--primary))', to: 'hsl(var(--primary) / 0.65)', ring: 'ring-primary/30' }
}

const statusTone = (status?: string | null) => {
  switch (status) {
    case NodeStatus.connected:
      return { dot: 'bg-emerald-400', text: 'text-emerald-400', bar: 'bg-emerald-500' }
    case NodeStatus.connecting:
      return { dot: 'bg-amber-400 animate-pulse', text: 'text-amber-400', bar: 'bg-amber-500' }
    case NodeStatus.limited:
      return { dot: 'bg-orange-400', text: 'text-orange-400', bar: 'bg-orange-500' }
    case NodeStatus.disabled:
      return { dot: 'bg-muted-foreground/50', text: 'text-muted-foreground', bar: 'bg-muted-foreground/40' }
    case NodeStatus.error:
    default:
      return { dot: 'bg-rose-400', text: 'text-rose-400', bar: 'bg-rose-500' }
  }
}

const SpecRow = ({
  icon: Icon,
  label,
  value,
  accent,
  mono,
}: {
  icon: typeof Globe
  label: string
  value: ReactNode
  accent?: string
  mono?: boolean
}) => (
  <div className="group flex items-start gap-3 rounded-xl px-1 py-2 transition-colors hover:bg-white/[0.03]">
    <div className={cn('mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-white/5 bg-white/[0.04]', accent)}>
      <Icon className="h-3.5 w-3.5" />
    </div>
    <div className="min-w-0 flex-1">
      <p className="text-muted-foreground text-[10px] font-semibold tracking-[0.16em] uppercase">{label}</p>
      <div className={cn('text-foreground mt-0.5 text-sm font-medium', mono && 'font-mono text-[13px]')}>{value}</div>
    </div>
  </div>
)

const LocationValue = ({ location, locale }: { location: InfraLocation; locale?: string }) => {
  const name = displayCountryName(location, locale)
  if (!name && !location.flag) {
    return <span className="text-muted-foreground">—</span>
  }
  return (
    <span className="inline-flex items-center gap-2">
      {name && <span>{name}</span>}
      {location.flag && <span className="text-base leading-none" aria-hidden>{location.flag}</span>}
    </span>
  )
}

const UsageBar = ({ label, percent, color, detail }: { label: string; percent: number; color: string; detail?: string }) => (
  <div className="space-y-2">
    <div className="flex items-center justify-between gap-2 text-[11px]">
      <span className="text-muted-foreground font-medium tracking-wide uppercase">{label}</span>
      <span className="font-mono tabular-nums">
        {detail ? `${detail} · ` : ''}
        {percent.toFixed(0)}%
      </span>
    </div>
    <div className="bg-muted/40 h-2 overflow-hidden rounded-full">
      <div className={cn('h-full rounded-full transition-all duration-700', color)} style={{ width: `${Math.min(100, Math.max(0, percent))}%` }} />
    </div>
  </div>
)

const NodeLeafCard = ({
  node,
  stats,
  locale,
  location,
}: {
  node: NodeResponse
  stats?: NodeRealtimeStats | null
  locale?: string
  location: InfraLocation
}) => {
  const { t } = useTranslation()
  const tone = statusTone(node.status)
  const country = displayCountryName(location, locale)
  const cpu = Math.min(100, Math.max(0, Number(stats?.cpu_usage) || 0))
  const memTotal = Number(stats?.mem_total) || 0
  const memUsed = Number(stats?.mem_used) || 0
  const memPct = memTotal > 0 ? (memUsed / memTotal) * 100 : 0

  return (
    <Card className="group border-border/50 bg-card/80 relative h-full overflow-hidden backdrop-blur-sm transition-all duration-300 hover:-translate-y-1 hover:border-primary/40 hover:shadow-[0_18px_50px_-28px_hsl(var(--primary)/0.55)]">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/40 to-transparent opacity-70" />
      <CardContent className="flex h-full flex-col gap-5 p-5 sm:p-6">
        <div className="border-border/40 flex items-start justify-between gap-3 border-b pb-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2.5">
              <span className={cn('h-2.5 w-2.5 shrink-0 rounded-full shadow-[0_0_10px_currentColor]', tone.dot)} />
              <h4 className="truncate text-[15px] font-semibold tracking-tight">{node.name}</h4>
            </div>
            <p className="text-muted-foreground mt-2 truncate font-mono text-[11px]">
              {node.address}
              {node.port ? `:${node.port}` : ''}
            </p>
          </div>
          <Badge variant="outline" className={cn('shrink-0 border-0 bg-white/[0.04] px-2.5 py-1 text-[10px] capitalize', tone.text)}>
            {t(`nodes.${node.status}`, { defaultValue: node.status })}
          </Badge>
        </div>

        <div className="border-border/40 space-y-3.5 rounded-2xl border bg-black/15 px-4 py-4">
          <div className="flex items-center justify-between gap-3">
            <span className="text-muted-foreground inline-flex items-center gap-1.5 text-[10px] font-semibold tracking-[0.14em] uppercase">
              <MapPin className="h-3.5 w-3.5" />
              {t('serverTopology.location', { defaultValue: 'Location' })}
            </span>
            <span className="inline-flex items-center gap-2 text-sm font-medium">
              {country || t('serverTopology.locationUnknown', { defaultValue: 'Unknown' })}
              {location.flag && <span className="text-base leading-none">{location.flag}</span>}
            </span>
          </div>
          <div className="border-border/30 border-t" />
          <div className="flex items-center justify-between gap-3">
            <span className="text-muted-foreground inline-flex items-center gap-1.5 text-[10px] font-semibold tracking-[0.14em] uppercase">
              <Building2 className="h-3.5 w-3.5" />
              {t('serverTopology.datacenter', { defaultValue: 'Datacenter' })}
            </span>
            <span className="truncate text-sm font-medium">{location.datacenter || '—'}</span>
          </div>
        </div>

        {stats ? (
          <div className="mt-auto space-y-4 pt-1">
            <UsageBar label="CPU" percent={cpu} color={tone.bar} />
            <UsageBar
              label="RAM"
              percent={memPct}
              color="bg-sky-500"
              detail={memTotal > 0 ? `${formatBytes(memUsed, 1)}/${formatBytes(memTotal, 1)}` : undefined}
            />
            <div className="text-muted-foreground flex items-center justify-between gap-3 border-t border-white/5 pt-4 font-mono text-[11px]">
              <span>
                {t('serverTopology.cores', { defaultValue: 'Cores' })} · {stats.cpu_cores || '—'}
              </span>
              <span>
                {t('serverTopology.uptime', { defaultValue: 'Uptime' })} · {formatCompactUptime(stats.uptime)}
              </span>
            </div>
          </div>
        ) : (
          <p className="text-muted-foreground mt-auto text-xs">{t('serverTopology.nodeStatsPending', { defaultValue: 'Live metrics unavailable' })}</p>
        )}
      </CardContent>
    </Card>
  )
}

const ServerTopologyCard = ({ resourceData, usersData, canReadNodes = false, canReadNodeStats = false }: ServerTopologyCardProps) => {
  const { t, i18n } = useTranslation()
  const dir = useDirDetection()
  const locale = i18n.resolvedLanguage || i18n.language

  const { data: nodesPayload, isLoading: nodesLoading } = useGetNodes(
    { limit: 100 },
    {
      query: {
        enabled: canReadNodes,
        refetchInterval: 15_000,
      },
    },
  )

  const { data: realtimeStats } = useRealtimeNodesStats({
    query: {
      enabled: canReadNodeStats,
      refetchInterval: 5_000,
    },
  })

  const nodes = nodesPayload?.nodes ?? []
  const locationsById = useResolvedInfraLocations(nodes)
  const connectedCount = nodes.filter(n => n.status === NodeStatus.connected).length
  const brand = resolveOsBrand(resourceData?.os_name)
  const osLine = [resourceData?.os_name, resourceData?.os_version].filter(Boolean).join(' ')
  const cpuFreq =
    resourceData?.cpu_freq_mhz != null && resourceData.cpu_freq_mhz > 0
      ? `${(resourceData.cpu_freq_mhz / 1000).toFixed(2)} GHz`
      : null
  const coresLine = resourceData?.cpu_cores
    ? `${resourceData.cpu_cores} ${resourceData.cpu_cores === 1 ? t('serverTopology.coreSingular', { defaultValue: 'Core' }) : t('serverTopology.corePlural', { defaultValue: 'Cores' })}${cpuFreq ? ` @ ${cpuFreq}` : ''}`
    : '—'
  const ramLine = resourceData?.mem_total != null ? formatBytes(Number(resourceData.mem_total), 2) : '—'
  const virtLine = resourceData?.virtualization
    ? t('serverTopology.virtualizedYes', { type: resourceData.virtualization.toUpperCase(), defaultValue: 'Yes ({{type}})' })
    : t('serverTopology.virtualizedNo', { defaultValue: 'Bare metal / Unknown' })

  const motherLocation = useMemo(() => {
    const fromHost = resolveInfraLocation(resourceData?.hostname)
    if (fromHost.countryCode || fromHost.datacenter) return fromHost
    return resolveLocationFromTimezone(resourceData?.timezone)
  }, [resourceData?.hostname, resourceData?.timezone])

  const cpuPct = Math.min(100, Math.max(0, Number(resourceData?.cpu_usage) || 0))
  const memPct =
    resourceData?.mem_total && resourceData.mem_total > 0 ? ((Number(resourceData.mem_used) || 0) / Number(resourceData.mem_total)) * 100 : 0

  const statsById = useMemo(() => {
    const map = new Map<number, NodeRealtimeStats | null>()
    if (!realtimeStats) return map
    for (const [key, value] of Object.entries(realtimeStats)) {
      map.set(Number(key), value)
    }
    return map
  }, [realtimeStats])

  if (!resourceData) {
    return (
      <Card className="border-border/60 overflow-hidden">
        <CardContent className="space-y-4 p-5">
          <Skeleton className="h-16 w-full rounded-2xl" />
          <Skeleton className="mx-auto h-8 w-1 rounded-full" />
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {[0, 1, 2].map(i => (
              <Skeleton key={i} className="h-48 rounded-2xl" />
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <section className="w-full" dir={dir} aria-label={t('serverTopology.title', { defaultValue: 'Server topology' })}>
      <div className="mb-4 flex items-end justify-between gap-3">
        <div>
          <p className="text-muted-foreground text-[11px] font-semibold tracking-[0.18em] uppercase">
            {t('serverTopology.eyebrow', { defaultValue: 'Infrastructure' })}
          </p>
          <h2 className="text-foreground mt-1 text-lg font-semibold tracking-tight sm:text-xl">
            {t('serverTopology.title', { defaultValue: 'Server topology' })}
          </h2>
          <p className="text-muted-foreground mt-1 max-w-xl text-sm">
            {nodes.length > 0
              ? t('serverTopology.subtitleTree', { defaultValue: 'Mother panel on top — connected nodes branch below' })
              : t('serverTopology.subtitleSolo', { defaultValue: 'Mother panel host identity and live resources' })}
          </p>
        </div>
        {canReadNodes && (
          <ButtonLikeLink to="/nodes" label={t('serverTopology.manageNodes', { defaultValue: 'Manage nodes' })} />
        )}
      </div>

      <div className="relative flex flex-col items-center">
        <Card
          className={cn(
            'border-border/70 relative w-full max-w-3xl overflow-hidden shadow-[0_24px_80px_-40px_rgba(0,0,0,0.65)]',
            'bg-gradient-to-br from-card via-card to-card/80',
          )}
        >
          <div
            className="pointer-events-none absolute -top-24 start-1/2 h-48 w-[120%] -translate-x-1/2 opacity-40 blur-3xl"
            style={{ background: `radial-gradient(ellipse at center, ${brand.from}55, transparent 70%)` }}
          />
          <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/25 to-transparent" />

          <CardContent className="relative space-y-5 p-5 sm:p-6">
            <div className="flex items-start gap-4">
              <div
                className={cn('flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl text-xl font-bold text-white shadow-lg ring-2', brand.ring)}
                style={{ background: `linear-gradient(145deg, ${brand.from}, ${brand.to})` }}
                aria-hidden
              >
                {brand.letter}
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge className="border-0 bg-primary/15 text-primary hover:bg-primary/20">
                    {t('serverTopology.mother', { defaultValue: 'Mother server' })}
                  </Badge>
                  <span className="inline-flex items-center gap-1.5 text-[11px] text-emerald-400">
                    <span className="relative flex h-2 w-2">
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
                      <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
                    </span>
                    {t('serverTopology.live', { defaultValue: 'Live' })}
                  </span>
                </div>
                <h3 className="mt-2 truncate text-xl font-semibold tracking-tight sm:text-2xl">{resourceData.hostname || 'panel'}</h3>
                <p className="text-muted-foreground mt-0.5 text-sm">{osLine || brand.label}</p>
              </div>
              <div className="hidden shrink-0 text-end sm:block">
                <p className="text-muted-foreground text-[10px] tracking-wider uppercase">{t('serverTopology.version', { defaultValue: 'Panel' })}</p>
                <p className="font-mono text-sm">v{resourceData.version}</p>
              </div>
            </div>

            <div className="grid gap-5 sm:grid-cols-[1.2fr_0.8fr]">
              <div className="grid gap-1 sm:grid-cols-2">
                <SpecRow
                  icon={MapPin}
                  label={t('serverTopology.panelLocation', { defaultValue: 'Panel location' })}
                  value={<LocationValue location={motherLocation} locale={locale} />}
                  accent="text-emerald-300"
                />
                <SpecRow
                  icon={Building2}
                  label={t('serverTopology.datacenter', { defaultValue: 'Datacenter' })}
                  value={motherLocation.datacenter || t('serverTopology.panelHost', { defaultValue: 'Panel host' })}
                  accent="text-teal-300"
                />
                <SpecRow
                  icon={Shield}
                  label={t('serverTopology.panelUptime', { defaultValue: 'Panel uptime' })}
                  value={formatCompactUptime(resourceData.uptime_seconds)}
                  accent="text-violet-300"
                  mono
                />
                <SpecRow
                  icon={Zap}
                  label={t('serverTopology.serverUptime', { defaultValue: 'Server uptime' })}
                  value={formatCompactUptime(resourceData.server_uptime_seconds)}
                  accent="text-amber-300"
                  mono
                />
                <SpecRow
                  icon={Network}
                  label={t('serverTopology.vpnServices', { defaultValue: 'VPN nodes' })}
                  value={
                    canReadNodes ? (
                      <span className="text-emerald-400">
                        {connectedCount} <span className="text-muted-foreground">/ {nodes.length}</span>
                      </span>
                    ) : (
                      <span className="text-muted-foreground">—</span>
                    )
                  }
                  accent="text-emerald-300"
                />
                <SpecRow
                  icon={Globe}
                  label={t('serverTopology.usersOnline', { defaultValue: 'Users online' })}
                  value={usersData ? `${usersData.online_users} / ${usersData.active_users}` : '—'}
                  accent="text-sky-300"
                />
                <SpecRow icon={Cpu} label={t('serverTopology.cpu', { defaultValue: 'CPU' })} value={resourceData.cpu_model || '—'} accent="text-rose-300" />
                <SpecRow icon={HardDrive} label={t('serverTopology.cores', { defaultValue: 'Cores' })} value={coresLine} accent="text-orange-300" />
                <SpecRow icon={MemoryStick} label={t('serverTopology.ram', { defaultValue: 'RAM' })} value={ramLine} accent="text-cyan-300" mono />
                <SpecRow icon={Box} label={t('serverTopology.kernel', { defaultValue: 'Kernel' })} value={resourceData.kernel || '—'} accent="text-lime-300" mono />
                <SpecRow icon={Server} label={t('serverTopology.virtualized', { defaultValue: 'Virtualized' })} value={virtLine} accent="text-fuchsia-300" />
              </div>

              <div className="border-border/50 flex flex-col justify-center gap-5 rounded-2xl border bg-black/20 p-4">
                <UsageBar
                  label={t('serverTopology.cpuLoad', { defaultValue: 'CPU load' })}
                  percent={cpuPct}
                  color="bg-rose-500"
                />
                <UsageBar
                  label={t('serverTopology.ramLoad', { defaultValue: 'Memory' })}
                  percent={memPct}
                  color="bg-sky-500"
                  detail={
                    resourceData.mem_used != null && resourceData.mem_total != null
                      ? `${formatBytes(Number(resourceData.mem_used), 1)}/${formatBytes(Number(resourceData.mem_total), 1)}`
                      : undefined
                  }
                />
                <div className="text-muted-foreground border-t border-white/5 pt-3 font-mono text-[10px]">
                  <p className="uppercase tracking-wider">{t('serverTopology.disk', { defaultValue: 'Disk' })}</p>
                  <p className="text-foreground mt-1 text-xs">
                    {resourceData.disk_used != null && resourceData.disk_total != null
                      ? `${formatBytes(Number(resourceData.disk_used), 1)} / ${formatBytes(Number(resourceData.disk_total), 1)}`
                      : '—'}
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {canReadNodes && (nodesLoading || nodes.length > 0) && (
          <>
            <div className="relative flex h-12 w-full flex-col items-center" aria-hidden>
              <div className="bg-gradient-to-b from-primary/60 to-primary/20 h-full w-px" />
              <div className="border-primary/30 absolute bottom-0 h-3 w-3 rounded-full border bg-background shadow-[0_0_12px_hsl(var(--primary)/0.45)]" />
            </div>

            {nodes.length > 0 && (
              <div className="relative mb-2 w-full max-w-6xl">
                <div className="mb-5 flex items-center justify-center">
                  <Badge variant="outline" className="bg-background/90 px-3 py-1 text-[10px] tracking-wider uppercase">
                    {t('serverTopology.nodesBranch', { count: nodes.length, defaultValue: '{{count}} nodes' })}
                  </Badge>
                </div>
                <div
                  className={cn(
                    'grid gap-5 sm:gap-6',
                    nodes.length === 1 && 'mx-auto max-w-md grid-cols-1',
                    nodes.length === 2 && 'mx-auto max-w-3xl grid-cols-1 sm:grid-cols-2',
                    nodes.length >= 3 && 'grid-cols-1 sm:grid-cols-2 xl:grid-cols-3',
                  )}
                >
                  {nodes.map(node => (
                    <NodeLeafCard
                      key={node.id}
                      node={node}
                      stats={statsById.get(node.id)}
                      locale={locale}
                      location={locationsById.get(String(node.id)) || resolveInfraLocation(node.name, node.address)}
                    />
                  ))}
                </div>
              </div>
            )}

            {nodesLoading && nodes.length === 0 && (
              <div className="grid w-full max-w-6xl gap-5 sm:grid-cols-2 xl:grid-cols-3">
                {[0, 1, 2].map(i => (
                  <Skeleton key={i} className="h-56 rounded-2xl" />
                ))}
              </div>
            )}
          </>
        )}

        {canReadNodes && !nodesLoading && nodes.length === 0 && (
          <p className="text-muted-foreground mt-5 text-center text-sm">
            {t('serverTopology.noNodes', { defaultValue: 'No nodes yet — mother server is running solo.' })}
          </p>
        )}
      </div>
    </section>
  )
}

const ButtonLikeLink = ({ to, label }: { to: string; label: string }) => (
  <Link
    to={to}
    className="text-primary hover:bg-primary/10 border-primary/20 hidden items-center rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors sm:inline-flex"
  >
    {label}
  </Link>
)

export default ServerTopologyCard
