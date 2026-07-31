import { Activity, Clock3, Cpu, Database, Download, HardDrive, MemoryStick, Upload } from 'lucide-react'
import { useTranslation } from 'react-i18next'

import useDirDetection from '@/hooks/use-dir-detection'
import { cn } from '@/lib/utils'
import type { NodeRealtimeStats, SystemResourceStats, SystemUsersStats } from '@/service/api'
import { formatBytes } from '@/utils/formatByte'
import { formatDuration } from '@/utils/formatDuration'

interface TelemetryBandProps {
  currentStats?: SystemResourceStats | NodeRealtimeStats | null
  usersStats?: SystemUsersStats
}

const isNodeStats = (stats: SystemResourceStats | NodeRealtimeStats): stats is NodeRealtimeStats => 'incoming_bandwidth_speed' in stats

const clampPercentage = (value: number) => Math.min(Math.max(value, 0), 100)

export default function TelemetryBand({ currentStats, usersStats }: TelemetryBandProps) {
  const { t } = useTranslation()
  const dir = useDirDetection()
  const nodeStats = currentStats && isNodeStats(currentStats) ? currentStats : null
  const nodeMode = !!nodeStats

  const cpuUsage = clampPercentage(Number(currentStats?.cpu_usage) || 0)
  const memoryUsed = Number(currentStats?.mem_used) || 0
  const memoryTotal = Number(currentStats?.mem_total) || 0
  const memoryUsage = clampPercentage(memoryTotal > 0 ? (memoryUsed / memoryTotal) * 100 : 0)
  const diskUsed = !nodeMode ? Number((currentStats as SystemResourceStats | undefined)?.disk_used) || 0 : 0
  const diskTotal = !nodeMode ? Number((currentStats as SystemResourceStats | undefined)?.disk_total) || 0 : 0
  const diskUsage = clampPercentage(diskTotal > 0 ? (diskUsed / diskTotal) * 100 : 0)
  const incoming = nodeStats ? Number(nodeStats.incoming_bandwidth_speed) || 0 : Number(usersStats?.incoming_bandwidth) || 0
  const outgoing = nodeStats ? Number(nodeStats.outgoing_bandwidth_speed) || 0 : Number(usersStats?.outgoing_bandwidth) || 0
  const uptimeSeconds = currentStats ? (nodeStats ? nodeStats.uptime : currentStats.uptime_seconds) : null
  const uptime = uptimeSeconds !== null ? formatDuration(uptimeSeconds, t) : '—'

  const telemetry = [
    {
      label: t('statistics.cpuUsage'),
      value: `${cpuUsage.toFixed(1)}%`,
      detail: `${Number(currentStats?.cpu_cores) || 0} ${t('statistics.cores')}`,
      percentage: cpuUsage,
      icon: Cpu,
      signal: true,
    },
    {
      label: t('statistics.ramUsage'),
      value: `${memoryUsage.toFixed(1)}%`,
      detail: `${formatBytes(memoryUsed, 1, false, false, 'GB')} / ${formatBytes(memoryTotal, 1, true, false, 'GB')}`,
      percentage: memoryUsage,
      icon: MemoryStick,
      signal: true,
    },
    nodeMode
      ? {
          label: t('statistics.downlink'),
          value: formatBytes(incoming, 1, true),
          detail: t('statistics.realTimeData'),
          icon: Download,
          signal: false,
        }
      : {
          label: t('statistics.diskUsage'),
          value: `${diskUsage.toFixed(1)}%`,
          detail: `${formatBytes(diskUsed, 1, false, false, 'GB')} / ${formatBytes(diskTotal, 1, true, false, 'GB')}`,
          percentage: diskUsage,
          icon: HardDrive,
          signal: true,
        },
    nodeMode
      ? {
          label: t('statistics.uplink'),
          value: formatBytes(outgoing, 1, true),
          detail: t('statistics.realTimeData'),
          icon: Upload,
          signal: false,
        }
      : {
          label: t('statistics.totalTraffic'),
          value: formatBytes(incoming + outgoing, 1),
          detail: `${formatBytes(incoming, 1)} ↓ · ${formatBytes(outgoing, 1)} ↑`,
          icon: Database,
          signal: false,
        },
    {
      label: t('statistics.uptime'),
      value: uptime,
      detail: nodeMode ? t('nodes.title') : t('master'),
      icon: Clock3,
      signal: false,
    },
  ]

  return (
    <section dir={dir} className="command-surface overflow-hidden" aria-labelledby="telemetry-heading">
      <div className="border-border flex items-center justify-between gap-3 border-b px-3 py-2.5 sm:px-4">
        <div className="flex min-w-0 items-center gap-2.5">
          <span className="bg-primary/10 text-primary flex h-7 w-7 shrink-0 items-center justify-center border border-current/20" aria-hidden="true">
            <Activity className="h-3.5 w-3.5" />
          </span>
          <div className="min-w-0">
            <p id="telemetry-heading" className="text-primary font-mono text-[10px] font-bold tracking-[0.16em] uppercase">
              01 / {t('statistics.system')}
            </p>
            <p className="text-muted-foreground truncate text-[11px]">{t('statistics.realtimeDescription')}</p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2" aria-label={t('statistics.realTimeData')}>
          <span className="online-beacon" aria-hidden="true" />
          <span className="hidden font-mono text-[9px] font-bold tracking-[0.14em] uppercase sm:inline">{t('statistics.realTimeData')}</span>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5">
        {telemetry.map((item, index) => {
          const Icon = item.icon
          return (
            <article
              key={item.label}
              className={cn(
                'group relative min-h-28 overflow-hidden px-3 py-3.5 sm:px-4',
                'border-border border-b md:border-b-0',
                index % 2 === 0 ? 'border-e' : '',
                index < telemetry.length - 1 && 'md:border-e',
                index === telemetry.length - 1 && 'col-span-2 md:col-span-1',
              )}
              aria-label={`${item.label}: ${item.value}`}
            >
              <div className="mb-4 flex items-start justify-between gap-2">
                <span className="text-muted-foreground font-mono text-[9px] font-bold tracking-[0.13em] uppercase">{item.label}</span>
                <Icon className="text-primary h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              </div>
              <p dir="ltr" className="font-mono text-xl leading-none font-bold tracking-tight tabular-nums">
                {item.value}
              </p>
              <p dir="ltr" className="text-muted-foreground mt-2 truncate font-mono text-[9px] tabular-nums">
                {item.detail}
              </p>
              {item.signal && (
                <div className="bg-muted absolute inset-x-0 bottom-0 h-0.5" aria-hidden="true">
                  <div className="bg-primary h-full transition-[width] duration-300" style={{ width: `${item.percentage ?? 0}%` }} />
                </div>
              )}
            </article>
          )
        })}
      </div>
    </section>
  )
}
