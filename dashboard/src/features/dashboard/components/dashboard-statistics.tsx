import { MiniSparkline } from '@/components/charts/mini-sparkline'
import { Skeleton } from '@/components/ui/skeleton'
import { UserStatsBars } from '@/components/ui/statistics-card'
import { Card, CardContent } from '@/components/ui/card'
import { useMetricHistory } from '@/hooks/use-metric-history'
import useDirDetection from '@/hooks/use-dir-detection'
import { cn } from '@/lib/utils'
import { SystemResourceStats, SystemUsersStats } from '@/service/api'
import { formatBytes } from '@/utils/formatByte'
import { Cpu, Database, Download, HardDrive, MemoryStick, Upload } from 'lucide-react'
import { type LucideIcon, type ReactNode } from 'react'
import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'

const DashboardStatistics = ({ resourceData, usersData }: { resourceData: SystemResourceStats | undefined; usersData: SystemUsersStats | undefined }) => {
  const { t } = useTranslation()
  const dir = useDirDetection()

  const memory = useMemo(() => {
    if (!resourceData) return { used: 0, total: 0, percentage: 0 }
    const memUsed = Number(resourceData.mem_used) || 0
    const memTotal = Number(resourceData.mem_total) || 0
    const percentage = memTotal > 0 ? (memUsed / memTotal) * 100 : 0
    return { used: memUsed, total: memTotal, percentage }
  }, [resourceData])

  const disk = useMemo(() => {
    if (!resourceData) return { used: 0, total: 0, percentage: 0 }
    const diskUsed = Number(resourceData.disk_used) || 0
    const diskTotal = Number(resourceData.disk_total) || 0
    const percentage = diskTotal > 0 ? (diskUsed / diskTotal) * 100 : 0
    return { used: diskUsed, total: diskTotal, percentage }
  }, [resourceData])

  const cpu = useMemo(() => {
    if (!resourceData) return { usage: 0, cores: 0 }
    let cpuUsage = Number(resourceData.cpu_usage) || 0
    const cpuCores = Number(resourceData.cpu_cores) || 0
    cpuUsage = Math.min(Math.max(cpuUsage, 0), 100)
    return { usage: Math.round(cpuUsage * 10) / 10, cores: cpuCores }
  }, [resourceData])

  const memoryPercent = Math.min(Math.max(memory.percentage, 0), 100)
  const diskPercent = Math.min(Math.max(disk.percentage, 0), 100)

  const historySample = resourceData
    ? { cpu: cpu.usage, mem: memoryPercent, disk: diskPercent }
    : null
  const history = useMetricHistory(historySample)

  const getTotalTrafficValue = () => {
    if (!usersData) return 0
    return Number(usersData.incoming_bandwidth) + Number(usersData.outgoing_bandwidth)
  }

  const getIncomingBandwidth = () => (usersData ? Number(usersData.incoming_bandwidth) || 0 : 0)
  const getOutgoingBandwidth = () => (usersData ? Number(usersData.outgoing_bandwidth) || 0 : 0)

  if (!resourceData && !usersData) {
    return (
      <div className={cn('grid h-full w-full gap-3', 'grid-cols-1 sm:grid-cols-2 xl:grid-cols-4')}>
        {[...Array(4)].map((_, i) => (
          <Card key={i} className="border-border/60 overflow-hidden rounded-xl">
            <CardContent className="space-y-3 p-4">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-8 w-24" />
              <Skeleton className="h-9 w-full rounded-md" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  const MetricCard = ({
    icon: Icon,
    label,
    value,
    detail,
    percent,
    sparkValues,
    sparkClass,
  }: {
    icon: LucideIcon
    label: string
    value: ReactNode
    detail?: ReactNode
    percent?: number
    sparkValues: number[]
    sparkClass: string
  }) => (
    <Card dir={dir} className="border-border/50 bg-card/40 group relative overflow-hidden rounded-xl transition-[border-color,box-shadow] duration-200 hover:border-primary/25 hover:shadow-sm">
      <CardContent className="flex h-full flex-col gap-3 p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2">
            <Icon className="text-muted-foreground h-3.5 w-3.5 shrink-0" />
            <span className="text-muted-foreground truncate text-[11px] font-medium tracking-wide uppercase">{label}</span>
          </div>
          {percent != null && (
            <span dir="ltr" className="text-muted-foreground shrink-0 font-mono text-[11px] tabular-nums">
              {percent.toFixed(1)}%
            </span>
          )}
        </div>
        <div className="min-w-0">
          <p dir="ltr" className="text-foreground text-xl font-semibold tracking-tight break-words tabular-nums sm:text-2xl">
            {value}
          </p>
          {detail && <p className="text-muted-foreground mt-1 text-[11px] leading-snug">{detail}</p>}
        </div>
        <div className="text-sky-500/80 mt-auto pt-1">
          <MiniSparkline values={sparkValues} strokeClassName={sparkClass} />
        </div>
      </CardContent>
    </Card>
  )

  const cpuSeries = history.map(p => p.cpu)
  const memSeries = history.map(p => p.mem)
  const diskSeries = history.map(p => p.disk)

  return (
    <div className="flex w-full flex-col gap-4">
      <div className={cn('grid w-full gap-3', 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4')}>
        <MetricCard
          icon={Cpu}
          label={t('statistics.cpuUsage')}
          value={`${cpu.usage}%`}
          detail={cpu.cores > 0 ? `${cpu.cores} ${t('statistics.cores')}` : undefined}
          sparkValues={cpuSeries.length > 1 ? cpuSeries : [cpu.usage, cpu.usage]}
          sparkClass="stroke-rose-400"
        />
        <MetricCard
          icon={MemoryStick}
          label={t('statistics.ramUsage')}
          value={
            <>
              {formatBytes(memory.used, 1, false, false, 'GB')}
              <span className="text-muted-foreground text-base font-normal"> / {formatBytes(memory.total, 1, true, false, 'GB')}</span>
            </>
          }
          percent={memoryPercent}
          sparkValues={memSeries.length > 1 ? memSeries : [memoryPercent, memoryPercent]}
          sparkClass="stroke-sky-400"
        />
        <MetricCard
          icon={HardDrive}
          label={t('statistics.diskUsage')}
          value={
            <>
              {formatBytes(disk.used, 1, false, false, 'GB')}
              <span className="text-muted-foreground text-base font-normal"> / {formatBytes(disk.total, 1, true, false, 'GB')}</span>
            </>
          }
          percent={diskPercent}
          sparkValues={diskSeries.length > 1 ? diskSeries : [diskPercent, diskPercent]}
          sparkClass="stroke-amber-400"
        />
        {usersData && (
          <MetricCard
            icon={Database}
            label={t('statistics.totalTraffic')}
            value={formatBytes(getTotalTrafficValue() || 0, 1)}
            detail={t('statistics.lifetimeTraffic', { defaultValue: 'Lifetime total' })}
            sparkValues={[getIncomingBandwidth(), getOutgoingBandwidth(), getTotalTrafficValue()].map(v => (v > 0 ? Math.log10(v + 1) * 10 : 0))}
            sparkClass="stroke-violet-400"
          />
        )}
      </div>

      {usersData && (
        <Card dir={dir} className="border-border/50 bg-card/40 overflow-hidden rounded-xl">
          <CardContent className="grid gap-4 p-4 sm:grid-cols-2">
            <div className="bg-muted/30 rounded-lg px-3 py-3">
              <p className="text-muted-foreground flex items-center gap-1.5 text-[10px] font-semibold tracking-wider uppercase">
                <Download className="h-3.5 w-3.5 text-emerald-400" />
                {t('statistics.download', { defaultValue: 'Download' })}
              </p>
              <p dir="ltr" className="mt-2 text-lg font-semibold tabular-nums text-emerald-400">
                {formatBytes(getIncomingBandwidth() || 0, 1)}
              </p>
            </div>
            <div className="bg-muted/30 rounded-lg px-3 py-3">
              <p className="text-muted-foreground flex items-center gap-1.5 text-[10px] font-semibold tracking-wider uppercase">
                <Upload className="h-3.5 w-3.5 text-sky-400" />
                {t('statistics.upload', { defaultValue: 'Upload' })}
              </p>
              <p dir="ltr" className="mt-2 text-lg font-semibold tabular-nums text-sky-400">
                {formatBytes(getOutgoingBandwidth() || 0, 1)}
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {usersData && (
        <div className="w-full">
          <UserStatsBars data={usersData} />
        </div>
      )}
    </div>
  )
}

export default DashboardStatistics
