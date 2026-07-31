import { Skeleton } from '@/components/ui/skeleton'
import { NodeRealtimeStats, NodeSimple, SystemResourceStats, SystemUsersStats, useRealtimeNodeStats } from '@/service/api'
import { useEffect, useState, useCallback, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { CostumeBarChart } from '@/components/charts/costume-bar-chart'
import { EmptyState } from '@/components/charts/empty-state'
import UserSubUpdatePieChart from '@/components/charts/user-sub-update-pie-chart'
import TelemetryBand from './telemetry-band'
import { AllNodesStackedBarChart } from '@/components/charts/all-nodes-stacked-bar-chart'
import { AreaCostumeChart } from '@/components/charts/area-costume-chart'
import { Activity, AlertTriangle, Network, RadioTower, Users } from 'lucide-react'
import { UserCountsChart } from '@/components/charts/user-counts-chart'
import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

interface StatisticsChartsProps {
  data?: SystemResourceStats
  usersData?: SystemUsersStats
  isLoading: boolean
  error?: { message?: string } | null
  selectedServer: string
  canViewNodeStats: boolean
  canViewSystemStats: boolean
  nodesData?: NodeSimple[]
  isLoadingNodes?: boolean
}

export default function StatisticsCharts({ data, usersData, isLoading, error, selectedServer, canViewNodeStats, canViewSystemStats, nodesData = [], isLoadingNodes = false }: StatisticsChartsProps) {
  const { t } = useTranslation()

  // Remount charts after viewport geometry changes (fullscreen often changes height only).
  const [chartRefreshKey, setChartRefreshKey] = useState(0)
  const resizeTimeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined)
  const lastViewportRef = useRef({
    width: typeof window !== 'undefined' ? window.innerWidth : 0,
    height: typeof window !== 'undefined' ? window.innerHeight : 0,
  })

  const actualSelectedServer = selectedServer === 'master' && !canViewSystemStats ? '' : canViewNodeStats ? selectedServer : 'master'
  const selectedNodeId = actualSelectedServer && actualSelectedServer !== 'master' ? parseInt(actualSelectedServer, 10) : undefined
  const selectedNode = selectedNodeId !== undefined ? nodesData.find(node => node.id === selectedNodeId) : undefined
  const selectedNodeConnected = selectedNode?.status === 'connected'
  const shouldFetchNodeRealtime = canViewNodeStats && !!selectedNodeId && selectedNodeConnected

  // Only fetch realtime node stats for connected nodes.
  const { data: nodeStats, isLoading: isLoadingNodeStats } = useRealtimeNodeStats(selectedNodeId || 0, {
    query: {
      enabled: shouldFetchNodeRealtime,
      refetchInterval: 1500, // Update every 1.5 seconds for faster realtime updates
      staleTime: 1000, // Consider data stale after 1 second
    },
  })

  const scheduleChartRefresh = useCallback(() => {
    if (resizeTimeoutRef.current) {
      clearTimeout(resizeTimeoutRef.current)
    }
    resizeTimeoutRef.current = setTimeout(() => {
      setChartRefreshKey(k => k + 1)
    }, 120)
  }, [])

  const handleResize = useCallback(() => {
    const next = {
      width: window.innerWidth,
      height: window.innerHeight,
    }
    const prev = lastViewportRef.current
    if (next.width === prev.width && next.height === prev.height) {
      return
    }
    lastViewportRef.current = next
    scheduleChartRefresh()
  }, [scheduleChartRefresh])

  useEffect(() => {
    window.addEventListener('resize', handleResize)
    window.visualViewport?.addEventListener('resize', handleResize)

    const handleFullscreenChange = () => {
      // Fullscreen toggles can fire before final layout settles.
      scheduleChartRefresh()
      window.setTimeout(scheduleChartRefresh, 250)
    }
    document.addEventListener('fullscreenchange', handleFullscreenChange)

    const handleSidebarToggle = () => {
      window.setTimeout(scheduleChartRefresh, 300)
    }
    window.addEventListener('sidebar-toggle', handleSidebarToggle)

    return () => {
      window.removeEventListener('resize', handleResize)
      window.visualViewport?.removeEventListener('resize', handleResize)
      document.removeEventListener('fullscreenchange', handleFullscreenChange)
      window.removeEventListener('sidebar-toggle', handleSidebarToggle)
      if (resizeTimeoutRef.current) {
        clearTimeout(resizeTimeoutRef.current)
      }
    }
  }, [handleResize, scheduleChartRefresh])

  if ((actualSelectedServer === 'master' && isLoading) || (canViewNodeStats && isLoadingNodes) || (shouldFetchNodeRealtime && isLoadingNodeStats)) {
    return <StatisticsSkeletons canViewNodeStats={canViewNodeStats} />
  }

  if (error) {
    return (
      <section className="command-surface min-h-[420px] overflow-hidden" aria-labelledby="statistics-error-heading">
        <div className="border-border flex items-center gap-3 border-b px-4 py-3">
          <AlertTriangle className="text-destructive h-4 w-4" aria-hidden="true" />
          <div>
            <p className="text-destructive font-mono text-[10px] font-bold tracking-[0.14em] uppercase">Telemetry fault</p>
            <h2 id="statistics-error-heading" className="text-sm font-semibold">
              {t('errors.statisticsLoadFailed')}
            </h2>
          </div>
        </div>
        <EmptyState type="error" title={t('errors.statisticsLoadFailed')} description={error?.message || t('errors.connectionFailed')} className="min-h-[350px]" />
      </section>
    )
  }

  if (!actualSelectedServer) {
    return <EmptyState type="no-data" title={t('selectServer')} description={t('statistics.selectNodeToView')} className="min-h-[400px]" />
  }

  // Get the current stats based on selection
  const currentStats = actualSelectedServer === 'master' ? data : selectedNodeConnected ? (nodeStats as NodeRealtimeStats) : null
  const showRealtimeSystemStats = (actualSelectedServer === 'master' && !!data) || selectedNodeConnected
  const showSubscription = actualSelectedServer === 'master'
  const trafficIndex = '02'
  const userCountIndex = canViewNodeStats ? '03' : '02'
  const subscriptionIndex = canViewNodeStats ? '04' : '03'
  const realtimeIndex = showSubscription ? (canViewNodeStats ? '05' : '04') : canViewNodeStats ? '04' : '03'

  return (
    <div className="flex min-w-0 flex-col gap-4">
      {showRealtimeSystemStats && (
        <div className="animate-rise" style={{ animationDuration: '450ms', animationDelay: '60ms', animationFillMode: 'both' }}>
          <TelemetryBand currentStats={currentStats} usersStats={actualSelectedServer === 'master' ? usersData : undefined} />
        </div>
      )}

      {/* Balanced theater grid — avoids the fullscreen void under a short left column. */}
      <div className="grid min-w-0 auto-rows-fr grid-cols-1 gap-4 xl:grid-cols-2">
        {canViewNodeStats && (
          <TheaterFrame
            index={trafficIndex}
            label={t('statistics.trafficUsage')}
            caption={t('statistics.trafficUsageDescription')}
            icon={<Network className="h-3.5 w-3.5" aria-hidden="true" />}
            className="animate-rise min-h-0 min-w-0"
          >
            {actualSelectedServer === 'master' ? <AllNodesStackedBarChart key={`traffic-all-${chartRefreshKey}`} /> : <CostumeBarChart key={`traffic-node-${chartRefreshKey}`} nodeId={selectedNodeId} />}
          </TheaterFrame>
        )}

        <TheaterFrame
          index={userCountIndex}
          label={t('statistics.userCountChart', { defaultValue: 'User Count' })}
          caption={t('statistics.userCountChartDescription', { defaultValue: 'Online, expired, and limited user activity counts over time' })}
          icon={<Users className="h-3.5 w-3.5" aria-hidden="true" />}
          className="min-h-0 min-w-0"
        >
          <UserCountsChart key={`users-${chartRefreshKey}`} nodeId={selectedNodeId} isSudo={canViewNodeStats} nodesData={nodesData} />
        </TheaterFrame>

        {showSubscription && (
          <TheaterFrame
            index={subscriptionIndex}
            label={t('statistics.subscriptionDistribution')}
            caption={t('statistics.subscriptionDistributionDescription')}
            icon={<RadioTower className="h-3.5 w-3.5" aria-hidden="true" />}
            className="min-h-0 min-w-0"
          >
            <UserSubUpdatePieChart key={`subs-${chartRefreshKey}`} />
          </TheaterFrame>
        )}

        <TheaterFrame
          index={realtimeIndex}
          label={t('statistics.realTimeData')}
          caption={t('statistics.realtimeDescription')}
          icon={<Activity className="h-3.5 w-3.5" aria-hidden="true" />}
          className={cn('animate-rise min-h-0 min-w-0', !showSubscription && canViewNodeStats && 'xl:col-span-2')}
        >
          <AreaCostumeChart
            key={`area-${chartRefreshKey}`}
            nodeId={selectedNodeId}
            currentStats={currentStats}
            realtimeStats={actualSelectedServer === 'master' ? data : selectedNodeConnected ? nodeStats || undefined : undefined}
            realtimeAvailable={actualSelectedServer === 'master' || selectedNodeConnected}
          />
        </TheaterFrame>
      </div>
    </div>
  )
}

function StatisticsSkeletons({ canViewNodeStats }: { canViewNodeStats: boolean }) {
  return (
    <div className="flex min-w-0 flex-col gap-4" aria-busy="true" aria-label="Loading network telemetry">
      <div className="command-surface grid grid-cols-2 overflow-hidden md:grid-cols-5">
        {[1, 2, 3, 4, 5].map(i => (
          <div key={i} className="border-border min-h-28 border-e p-4">
            <Skeleton className="mb-5 h-3 w-16" />
            <Skeleton className="h-7 w-24" />
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        {canViewNodeStats && <Skeleton className="h-[420px] w-full rounded-none" />}
        <Skeleton className="h-[420px] w-full rounded-none" />
        <Skeleton className="h-[360px] w-full rounded-none" />
        <Skeleton className={cn('h-[360px] w-full rounded-none', !canViewNodeStats && 'xl:col-span-2')} />
      </div>
    </div>
  )
}

interface TheaterFrameProps {
  index: string
  label: string
  caption: string
  icon: ReactNode
  children: ReactNode
  className?: string
}

function TheaterFrame({ index, label, caption, icon, children, className }: TheaterFrameProps) {
  const headingId = `theater-${index.replace(/\D/g, '')}-${label.replace(/\s+/g, '-').toLowerCase()}`

  return (
    <section className={cn('command-surface flex h-full min-h-0 min-w-0 flex-col overflow-hidden', className)} aria-labelledby={headingId}>
      <div className="border-border flex shrink-0 items-center justify-between gap-4 border-b px-3 py-2.5 sm:px-4">
        <div className="flex min-w-0 items-center gap-2.5">
          <span className="text-primary flex shrink-0 items-center gap-1.5 font-mono text-[10px] font-bold tracking-[0.15em]">
            {index}
            <span aria-hidden="true">/</span>
            {icon}
          </span>
          <div className="min-w-0">
            <h2 id={headingId} className="truncate font-mono text-[10px] font-bold tracking-[0.13em] uppercase">
              {label}
            </h2>
            <p className="text-muted-foreground hidden truncate text-[10px] sm:block">{caption}</p>
          </div>
        </div>
        <span className="command-signal shrink-0" aria-hidden="true">
          <span />
          <span />
          <span />
        </span>
      </div>
      <div className="flex min-h-0 min-w-0 flex-1 flex-col [&>div]:h-full [&>div]:min-h-0 [&>div]:rounded-none [&>div]:border-0 [&>div]:shadow-none">{children}</div>
    </section>
  )
}
