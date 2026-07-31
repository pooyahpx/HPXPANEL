import MainContent from '@/features/statistics/components/statistics-charts'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useGetSystemResourceStats, useGetSystemUsersStats, useGetNodesSimple, NodeSimple, NodeStatus } from '@/service/api'
import { cn } from '@/lib/utils'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Skeleton } from '@/components/ui/skeleton'
import { useAdmin } from '@/hooks/use-admin'
import { hasPermission } from '@/utils/rbac'
import useDirDetection from '@/hooks/use-dir-detection'
import { Activity, Crosshair, RadioTower, Server, ShieldCheck } from 'lucide-react'

const Statistics = () => {
  const { t } = useTranslation()
  const dir = useDirDetection()
  const [selectedServer, setSelectedServer] = useState<string>('master')
  const { admin } = useAdmin()
  const canViewNodeStats = hasPermission(admin, 'nodes', 'stats')
  const canViewSystemStats = hasPermission(admin, 'system', 'read')

  // Fetch nodes for the selector
  const { data: nodesResponse, isLoading: isLoadingNodes } = useGetNodesSimple(
    { all: true },
    {
      query: {
        enabled: canViewNodeStats,
      },
    },
  )

  // Extract nodes array from response
  const nodesData = nodesResponse?.nodes || []
  const selectedNode = selectedServer === 'master' ? undefined : nodesData.find(node => String(node.id) === selectedServer)
  const selectedScopeName = selectedServer === 'master' ? t('master') : selectedNode?.name || t('selectServer')
  const connectedNodes = nodesData.filter(node => node.status === 'connected').length

  useEffect(() => {
    if (canViewSystemStats || selectedServer !== 'master') return

    const firstNode = nodesData[0]
    if (firstNode) {
      setSelectedServer(String(firstNode.id))
    }
  }, [canViewSystemStats, nodesData, selectedServer])

  const getNodeStatusDotColor = (status: NodeStatus) => {
    switch (status) {
      case 'connected':
        return 'bg-green-500'
      case 'connecting':
        return 'bg-amber-500'
      case 'error':
        return 'bg-destructive'
      case 'limited':
        return 'bg-orange-500'
      default:
        return 'bg-gray-400 dark:bg-gray-600'
    }
  }

  const {
    data: resourceData,
    error,
    isLoading,
  } = useGetSystemResourceStats({
    query: {
      enabled: canViewSystemStats && selectedServer === 'master',
      refetchInterval: canViewSystemStats && selectedServer === 'master' ? 2000 : false,
      staleTime: 1000,
      refetchOnWindowFocus: true,
    },
  })

  const { data: usersData } = useGetSystemUsersStats(undefined, {
    query: {
      enabled: canViewSystemStats && selectedServer === 'master',
      refetchInterval: canViewSystemStats && selectedServer === 'master' ? 2000 : false,
      staleTime: 1000,
      refetchOnWindowFocus: true,
    },
  })

  const showScopeRail = canViewNodeStats && (canViewSystemStats || nodesData.length > 0)

  return (
    <div dir={dir} className="w-full">
      <header className="mission-brief relative overflow-hidden border-b" aria-labelledby="operations-theater-title">
        <div className="mission-brief__index" aria-hidden="true">
          NOC
        </div>
        <div className="relative z-10 mx-auto flex w-full max-w-[1800px] flex-col gap-5 px-4 py-6 md:px-6 md:py-8 lg:flex-row lg:items-end lg:justify-between">
          <div className="border-primary max-w-3xl border-s-2 ps-4">
            <div className="text-primary mb-2 flex items-center gap-2 font-mono text-[10px] font-bold tracking-[0.18em] uppercase">
              <Crosshair className="h-3.5 w-3.5" aria-hidden="true" />
              HPXPANEL / Network Operations Theater
            </div>
            <h1 id="operations-theater-title" className="font-display text-3xl leading-none font-black tracking-[-0.04em] uppercase sm:text-4xl lg:text-5xl">
              {t('statistics')}
            </h1>
            <p className="text-muted-foreground mt-2 max-w-2xl text-xs leading-relaxed sm:text-sm">{t('monitorServers')}</p>
          </div>

          <div className="grid grid-cols-3 border" aria-label="Operations status">
            <div className="border-border min-w-24 border-e px-3 py-2.5">
              <p className="text-muted-foreground font-mono text-[8px] font-bold tracking-[0.14em] uppercase">{t('nodes.title')}</p>
              <p dir="ltr" className="mt-1 font-mono text-lg font-bold tabular-nums">
                {nodesData.length}
              </p>
            </div>
            <div className="border-border min-w-24 border-e px-3 py-2.5">
              <p className="text-muted-foreground font-mono text-[8px] font-bold tracking-[0.14em] uppercase">Online</p>
              <p dir="ltr" className="text-primary mt-1 font-mono text-lg font-bold tabular-nums">
                {connectedNodes}
              </p>
            </div>
            <div className="min-w-24 px-3 py-2.5">
              <p className="text-muted-foreground font-mono text-[8px] font-bold tracking-[0.14em] uppercase">Poll rate</p>
              <p dir="ltr" className="mt-1 flex items-center gap-2 font-mono text-lg font-bold">
                <span className="online-beacon" aria-hidden="true" />
                LIVE
              </p>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-[1800px] min-w-0 px-3 py-4 sm:px-4 md:px-6 md:py-6" aria-label="Network operations statistics">
        <div className={cn('grid min-w-0 items-start gap-4', showScopeRail && 'xl:grid-cols-[minmax(0,220px)_minmax(0,1fr)]')}>
          {showScopeRail && (
            <aside className="command-surface min-w-0 overflow-hidden xl:sticky xl:top-24 xl:z-10 xl:max-h-[calc(100dvh-7.5rem)] xl:self-start" aria-labelledby="scope-heading">
              <div className="border-border flex items-center justify-between gap-3 border-b px-3 py-3">
                <div>
                  <p className="text-primary font-mono text-[9px] font-bold tracking-[0.16em] uppercase">00 / Scope</p>
                  <h2 id="scope-heading" className="mt-0.5 text-sm font-bold">
                    {t('nodes.title')}
                  </h2>
                </div>
                <RadioTower className="text-primary h-4 w-4" aria-hidden="true" />
              </div>

              <div className="border-border border-b p-3 xl:hidden">
                {isLoadingNodes ? (
                  <Skeleton className="h-10 w-full rounded-none" />
                ) : (
                  <Select value={selectedServer} onValueChange={setSelectedServer}>
                    <SelectTrigger className="h-10 w-full rounded-none font-mono text-xs">
                      <SelectValue placeholder={t('selectServer')} />
                    </SelectTrigger>
                    <SelectContent>
                      {canViewSystemStats && <SelectItem value="master">{t('master')}</SelectItem>}
                      {nodesData.map((node: NodeSimple) => (
                        <SelectItem key={node.id} value={String(node.id)}>
                          <span className="flex min-w-0 items-center gap-2">
                            <span className={cn('h-1.5 w-1.5 shrink-0 rounded-full', getNodeStatusDotColor(node.status))} aria-hidden="true" />
                            <span className="truncate">{node.name}</span>
                          </span>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </div>

              <nav className="hidden max-h-[calc(100dvh-16rem)] overflow-y-auto xl:block" aria-label={t('statistics.selectNodeToView')}>
                {canViewSystemStats && (
                  <button
                    type="button"
                    onClick={() => setSelectedServer('master')}
                    aria-current={selectedServer === 'master' ? 'true' : undefined}
                    className={cn(
                      'border-border focus-visible:ring-ring flex min-h-14 w-full items-center gap-3 border-b px-3 py-2.5 text-start transition-colors focus-visible:ring-2 focus-visible:outline-none',
                      selectedServer === 'master' ? 'bg-primary/10 text-primary' : 'hover:bg-muted/50',
                    )}
                  >
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center border border-current/20 bg-current/5">
                      <ShieldCheck className="h-4 w-4" aria-hidden="true" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-xs font-bold">{t('master')}</span>
                      <span className="text-muted-foreground block font-mono text-[8px] tracking-[0.12em] uppercase">Control plane</span>
                    </span>
                    {selectedServer === 'master' && <span className="h-6 w-0.5 bg-current" aria-hidden="true" />}
                  </button>
                )}

                {isLoadingNodes
                  ? [1, 2, 3].map(item => (
                      <div key={item} className="border-border border-b p-3">
                        <Skeleton className="h-8 w-full rounded-none" />
                      </div>
                    ))
                  : nodesData.map((node: NodeSimple) => {
                      const isSelected = selectedServer === String(node.id)
                      return (
                        <button
                          key={node.id}
                          type="button"
                          onClick={() => setSelectedServer(String(node.id))}
                          aria-current={isSelected ? 'true' : undefined}
                          className={cn(
                            'border-border focus-visible:ring-ring flex min-h-14 w-full items-center gap-3 border-b px-3 py-2.5 text-start transition-colors focus-visible:ring-2 focus-visible:outline-none',
                            isSelected ? 'bg-primary/10 text-primary' : 'hover:bg-muted/50',
                          )}
                        >
                          <span className="relative flex h-8 w-8 shrink-0 items-center justify-center border">
                            <Server className="h-3.5 w-3.5" aria-hidden="true" />
                            <span className={cn('ring-background absolute -end-1 -top-1 h-2 w-2 rounded-full ring-2', getNodeStatusDotColor(node.status))} aria-hidden="true" />
                          </span>
                          <span className="min-w-0 flex-1">
                            <span className="block truncate text-xs font-bold">{node.name}</span>
                            <span className="text-muted-foreground block font-mono text-[8px] tracking-[0.1em] uppercase">{node.status}</span>
                          </span>
                          {isSelected && <span className="h-6 w-0.5 bg-current" aria-hidden="true" />}
                        </button>
                      )
                    })}
              </nav>

              <div className="bg-muted/20 px-3 py-3">
                <div className="text-muted-foreground flex items-center gap-2 font-mono text-[8px] font-bold tracking-[0.13em] uppercase">
                  <Activity className="text-primary h-3 w-3" aria-hidden="true" />
                  Active theater
                </div>
                <p className="mt-1 truncate text-xs font-bold">{selectedScopeName}</p>
              </div>
            </aside>
          )}

          <section className="min-w-0" aria-label={`${selectedScopeName} telemetry`}>
            <MainContent
              error={error}
              isLoading={isLoading}
              data={resourceData}
              usersData={usersData}
              selectedServer={selectedServer}
              canViewNodeStats={canViewNodeStats}
              canViewSystemStats={canViewSystemStats}
              nodesData={nodesData}
              isLoadingNodes={isLoadingNodes}
            />
          </section>
        </div>
      </main>
    </div>
  )
}

export default Statistics
