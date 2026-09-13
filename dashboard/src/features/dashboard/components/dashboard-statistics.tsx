import { Skeleton } from '@/components/ui/skeleton'
import useDirDetection from '@/hooks/use-dir-detection'
import { cn } from '@/lib/utils'
import { SystemResourceStats, SystemUsersStats } from '@/service/api'
import { formatBytes } from '@/utils/formatByte'
import { Cpu, Database, Download, HardDrive, MemoryStick, Upload } from 'lucide-react'
import { type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { CircularProgress } from '@/components/ui/circular-progress'
import { Card, CardContent } from '@/components/ui/card'
import { UserStatsBars } from '@/components/ui/statistics-card'

const DashboardStatistics = ({ resourceData, usersData }: { resourceData: SystemResourceStats | undefined; usersData: SystemUsersStats | undefined }) => {
  const { t } = useTranslation()
  const dir = useDirDetection()

  if (!resourceData && !usersData) {
    return (
      <div className={cn('grid h-full w-full gap-4 sm:gap-5', 'grid-cols-1 sm:grid-cols-2 xl:grid-cols-4')}>
        {[...Array(4)].map((_, i) => (
          <Card key={i} className="h-full overflow-hidden border">
            <CardContent className="flex h-full flex-col gap-5 p-6">
              <Skeleton className="h-5 w-28" />
              <Skeleton className="h-10 w-32" />
              <Skeleton className="h-2 w-full rounded-full" />
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  const getTotalTrafficValue = () => {
    if (!usersData) return 0
    return Number(usersData.incoming_bandwidth) + Number(usersData.outgoing_bandwidth)
  }

  const getIncomingBandwidth = () => (usersData ? Number(usersData.incoming_bandwidth) || 0 : 0)
  const getOutgoingBandwidth = () => (usersData ? Number(usersData.outgoing_bandwidth) || 0 : 0)

  const memory = (() => {
    if (!resourceData) return { used: 0, total: 0, percentage: 0 }
    const memUsed = Number(resourceData.mem_used) || 0
    const memTotal = Number(resourceData.mem_total) || 0
    const percentage = memTotal > 0 ? (memUsed / memTotal) * 100 : 0
    return { used: memUsed, total: memTotal, percentage }
  })()

  const disk = (() => {
    if (!resourceData) return { used: 0, total: 0, percentage: 0 }
    const diskUsed = Number(resourceData.disk_used) || 0
    const diskTotal = Number(resourceData.disk_total) || 0
    const percentage = diskTotal > 0 ? (diskUsed / diskTotal) * 100 : 0
    return { used: diskUsed, total: diskTotal, percentage }
  })()

  const cpu = (() => {
    if (!resourceData) return { usage: 0, cores: 0 }
    let cpuUsage = Number(resourceData.cpu_usage) || 0
    const cpuCores = Number(resourceData.cpu_cores) || 0
    cpuUsage = Math.min(Math.max(cpuUsage, 0), 100)
    return { usage: Math.round(cpuUsage * 10) / 10, cores: cpuCores }
  })()

  const memoryPercent = Math.min(Math.max(memory.percentage, 0), 100)
  const diskPercent = Math.min(Math.max(disk.percentage, 0), 100)

  const StatCard = ({
    delay,
    icon: Icon,
    title,
    children,
  }: {
    delay: string
    icon: typeof Cpu
    title: string
    children: ReactNode
  }) => (
    <div className="animate-fade-in h-full w-full" style={{ animationDuration: '600ms', animationDelay: delay }}>
      <Card dir={dir} className="group border-border/60 relative h-full w-full overflow-hidden rounded-2xl transition-all duration-300 hover:border-primary/30 hover:shadow-lg">
        <div className="from-primary/10 absolute inset-0 bg-gradient-to-br to-transparent opacity-0 transition-opacity duration-500 group-hover:opacity-100 dark:from-primary/5" />
        <CardContent className="relative z-10 flex h-full flex-col p-5 sm:p-6">
          <div className="border-border/50 mb-5 flex items-center gap-3 border-b pb-4">
            <div className="bg-primary/10 rounded-xl p-2.5">
              <Icon className="text-primary h-4 w-4" />
            </div>
            <p className="text-muted-foreground truncate text-xs font-semibold tracking-[0.12em] uppercase sm:text-[13px]">{title}</p>
          </div>
          <div className="flex flex-1 flex-col justify-between gap-5">{children}</div>
        </CardContent>
      </Card>
    </div>
  )

  const Meter = ({ percent, color }: { percent: number; color: string }) => (
    <div className="bg-muted/50 h-2.5 w-full overflow-hidden rounded-full">
      <div className={cn('h-full rounded-full transition-all duration-700', color)} style={{ width: `${Math.min(100, Math.max(0, percent))}%` }} />
    </div>
  )

  return (
    <div className="flex w-full flex-col gap-5 sm:gap-6">
      <div className={cn('grid h-full w-full gap-4 sm:gap-5', 'grid-cols-1 sm:grid-cols-2 xl:grid-cols-4')}>
        <StatCard delay="50ms" icon={Cpu} title={t('statistics.cpuUsage')}>
          <div className="flex items-end justify-between gap-3">
            <div className="space-y-2">
              <p dir="ltr" className="text-3xl font-bold tracking-tight tabular-nums sm:text-4xl">
                {cpu.usage}%
              </p>
              {cpu.cores > 0 && (
                <p className="text-muted-foreground text-xs">
                  {cpu.cores} {t('statistics.cores')}
                </p>
              )}
            </div>
            <CircularProgress value={cpu.usage} size={48} strokeWidth={4} showValue={false} className="shrink-0 opacity-90" />
          </div>
          <Meter percent={cpu.usage} color="bg-rose-500" />
        </StatCard>

        <StatCard delay="120ms" icon={MemoryStick} title={t('statistics.ramUsage')}>
          <div className="flex items-end justify-between gap-3">
            <div className="min-w-0 space-y-2">
              <p dir="ltr" className="truncate text-2xl font-bold tracking-tight tabular-nums sm:text-3xl">
                {formatBytes(memory.used, 1, false, false, 'GB')}
                <span className="text-muted-foreground text-base font-medium"> / {formatBytes(memory.total, 1, true, false, 'GB')}</span>
              </p>
              <p className="text-muted-foreground text-xs tabular-nums">{memoryPercent.toFixed(1)}%</p>
            </div>
            <CircularProgress value={memoryPercent} size={48} strokeWidth={4} showValue={false} className="shrink-0 opacity-90" />
          </div>
          <Meter percent={memoryPercent} color="bg-sky-500" />
        </StatCard>

        <StatCard delay="190ms" icon={HardDrive} title={t('statistics.diskUsage')}>
          <div className="flex items-end justify-between gap-3">
            <div className="min-w-0 space-y-2">
              <p dir="ltr" className="truncate text-2xl font-bold tracking-tight tabular-nums sm:text-3xl">
                {formatBytes(disk.used, 1, false, false, 'GB')}
                <span className="text-muted-foreground text-base font-medium"> / {formatBytes(disk.total, 1, true, false, 'GB')}</span>
              </p>
              <p className="text-muted-foreground text-xs tabular-nums">{diskPercent.toFixed(1)}%</p>
            </div>
            <CircularProgress value={diskPercent} size={48} strokeWidth={4} showValue={false} className="shrink-0 opacity-90" />
          </div>
          <Meter percent={diskPercent} color="bg-amber-500" />
        </StatCard>

        {usersData && (
          <StatCard delay="260ms" icon={Database} title={t('statistics.totalTraffic')}>
            <div className="space-y-2">
              <p dir="ltr" className="text-3xl font-bold tracking-tight tabular-nums sm:text-4xl">
                {formatBytes(getTotalTrafficValue() || 0, 1)}
              </p>
              <p className="text-muted-foreground text-xs">{t('statistics.lifetimeTraffic', { defaultValue: 'Lifetime total' })}</p>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-muted/40 rounded-xl px-3 py-3">
                <p className="text-muted-foreground flex items-center gap-1.5 text-[10px] font-semibold tracking-wider uppercase">
                  <Download className="h-3.5 w-3.5 text-emerald-400" />
                  {t('statistics.download', { defaultValue: 'Download' })}
                </p>
                <p dir="ltr" className="mt-2 text-sm font-semibold tabular-nums text-emerald-400">
                  {formatBytes(getIncomingBandwidth() || 0, 1)}
                </p>
              </div>
              <div className="bg-muted/40 rounded-xl px-3 py-3">
                <p className="text-muted-foreground flex items-center gap-1.5 text-[10px] font-semibold tracking-wider uppercase">
                  <Upload className="h-3.5 w-3.5 text-sky-400" />
                  {t('statistics.upload', { defaultValue: 'Upload' })}
                </p>
                <p dir="ltr" className="mt-2 text-sm font-semibold tabular-nums text-sky-400">
                  {formatBytes(getOutgoingBandwidth() || 0, 1)}
                </p>
              </div>
            </div>
          </StatCard>
        )}
      </div>

      {usersData && (
        <div className="animate-fade-in w-full" style={{ animationDuration: '600ms', animationDelay: '320ms' }}>
          <UserStatsBars data={usersData} />
        </div>
      )}
    </div>
  )
}

export default DashboardStatistics
