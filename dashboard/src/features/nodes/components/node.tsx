import { Card } from '@/components/ui/card'
import { AlertCircle, Link2, Network, Package, Server, ShieldCheck } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import useDirDetection from '@/hooks/use-dir-detection'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { Separator } from '@/components/ui/separator'
import { cn } from '@/lib/utils'
import { CoresSimpleResponse, NodeResponse } from '@/service/api'
import { useXrayReleases } from '@/hooks/use-xray-releases'
import { useNodeReleases } from '@/hooks/use-node-releases'
import NodeUsageDisplay from './node-usage-display'
import NodeActionsMenu from './node-actions-menu'
import UpdateCoreDialog from '@/features/nodes/dialogs/update-core-modal'
import { useState } from 'react'
import type { MouseEvent, ReactNode } from 'react'
import { Badge } from '@/components/ui/badge'

interface NodeProps {
  node: NodeResponse
  onEdit: (node: NodeResponse) => void
  onToggleStatus: (node: NodeResponse) => Promise<void>
  coresData?: CoresSimpleResponse
  canUpdate?: boolean
  canDelete?: boolean
  canReconnect?: boolean
  canUpdateCore?: boolean
  canReadStats?: boolean
  selectionControl?: ReactNode
  selected?: boolean
}

export default function Node({
  node,
  onEdit,
  onToggleStatus,
  coresData,
  canUpdate = true,
  canDelete = true,
  canReconnect = true,
  canUpdateCore = true,
  canReadStats = true,
  selectionControl,
  selected = false,
}: NodeProps) {
  const { t } = useTranslation()
  const dir = useDirDetection()
  const [showUpdateCoreDialog, setShowUpdateCoreDialog] = useState(false)
  const { latestVersion: latestXrayVersion, hasUpdate: hasXrayUpdate } = useXrayReleases()
  const { latestVersion: latestNodeVersion, hasUpdate: hasNodeUpdate } = useNodeReleases()
  const coreVersion = node.core_version ?? node.xray_version
  const resolvedCore = coresData?.cores?.find(c => c.id === node.core_config_id)
  const resolvedCoreType = resolvedCore?.type ?? null
  const resolvedCoreTypeString = String(resolvedCoreType ?? 'xray')
  const isWireGuardCore = resolvedCoreType === 'wg'
  const isXrayBackend = resolvedCoreType !== 'wg'
  const coreUpdateVersion = node.xray_version ?? coreVersion
  const hasCoreUpdate = !!(isXrayBackend && coreUpdateVersion && latestXrayVersion && hasXrayUpdate(coreUpdateVersion))
  const hasNodeVersionUpdate = !isWireGuardCore && !!latestNodeVersion && !!node.node_version && hasNodeUpdate(node.node_version)

  const getStatusConfig = () => {
    switch (node.status) {
      case 'connected':
        return {
          label: t('nodeModal.status.connected', { defaultValue: 'Connected' }),
          badge: 'border-emerald-500/35 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
          ring: 'border-emerald-500/25',
          dot: 'bg-emerald-500',
        }
      case 'connecting':
        return {
          label: t('nodeModal.status.connecting', { defaultValue: 'Connecting' }),
          badge: 'border-amber-500/35 bg-amber-500/10 text-amber-700 dark:text-amber-400',
          ring: 'border-amber-500/25',
          dot: 'bg-amber-500',
        }
      case 'error':
        return {
          label: t('nodeModal.status.error', { defaultValue: 'Error' }),
          badge: 'border-destructive/35 bg-destructive/10 text-destructive',
          ring: 'border-destructive/30',
          dot: 'bg-destructive',
        }
      case 'limited':
        return {
          label: t('status.limited', { defaultValue: 'Limited' }),
          badge: 'border-orange-500/35 bg-orange-500/10 text-orange-700 dark:text-orange-400',
          ring: 'border-orange-500/25',
          dot: 'bg-orange-500',
        }
      default:
        return {
          label: t('nodeModal.status.disabled', { defaultValue: 'Disabled' }),
          badge: 'border-border bg-muted/40 text-muted-foreground',
          ring: 'border-border/70',
          dot: 'bg-muted-foreground/50',
        }
    }
  }

  const statusConfig = getStatusConfig()
  const uplink = node.uplink || 0
  const downlink = node.downlink || 0
  const totalUsed = uplink + downlink
  const lifetimeUplink = node.lifetime_uplink || 0
  const lifetimeDownlink = node.lifetime_downlink || 0
  const totalLifetime = lifetimeUplink + lifetimeDownlink
  const hasUsageDisplay = !(totalUsed === 0 && !node.data_limit && totalLifetime === 0)

  const handleCoreVersionClick = (event: MouseEvent<HTMLButtonElement>) => {
    if (!canUpdateCore || !hasCoreUpdate) return
    event.preventDefault()
    event.stopPropagation()
    setShowUpdateCoreDialog(true)
  }

  const TypeIcon = resolvedCoreTypeString === 'ikev2' ? ShieldCheck : resolvedCoreTypeString === 'l2tp' ? Network : null

  return (
    <TooltipProvider>
      <Card
        className={cn(
          'group relative h-full overflow-hidden border transition-all duration-200',
          statusConfig.ring,
          canUpdate && 'hover:bg-accent/40 cursor-pointer hover:shadow-sm',
          selected && 'border-primary/50 bg-accent/30 ring-primary/20 ring-1',
        )}
        onClick={() => {
          if (canUpdate) onEdit(node)
        }}
      >
        <div className="flex items-start gap-3 p-4 sm:p-5">
          {selectionControl ? <div className="pt-1.5">{selectionControl}</div> : null}
          <div className="min-w-0 flex-1 space-y-4">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1 space-y-2.5">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="outline" className={cn('h-6 gap-1.5 px-2 text-[10px] font-semibold tracking-wide uppercase', statusConfig.badge)}>
                    <span className={cn('h-1.5 w-1.5 rounded-full', statusConfig.dot)} />
                    {statusConfig.label}
                  </Badge>
                  <Badge variant="outline" className="h-6 gap-1 px-2 text-[10px] font-medium tracking-wide uppercase">
                    {TypeIcon ? <TypeIcon className="h-3 w-3" /> : null}
                    {t(`coreTypes.${resolvedCoreTypeString}`, {
                      defaultValue: resolvedCoreTypeString === 'wg' ? 'WireGuard' : resolvedCoreTypeString === 'xray' ? 'Xray' : resolvedCoreTypeString.toUpperCase(),
                    })}
                  </Badge>
                  {node.status === 'error' && node.message ? (
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <AlertCircle className="text-destructive h-4 w-4 shrink-0 cursor-help" />
                      </TooltipTrigger>
                      <TooltipContent className="max-w-xs" side="top">
                        <p className="text-xs">{node.message}</p>
                      </TooltipContent>
                    </Tooltip>
                  ) : null}
                </div>

                <div className="space-y-1">
                  <h3 className="truncate text-base leading-tight font-semibold tracking-tight sm:text-lg">{node.name}</h3>
                  {resolvedCore?.name ? <p className="text-muted-foreground truncate text-xs">{resolvedCore.name}</p> : null}
                </div>
              </div>

              <NodeActionsMenu
                node={node}
                onEdit={onEdit}
                onToggleStatus={onToggleStatus}
                coresData={coresData}
                isModalHost={false}
                canUpdate={canUpdate}
                canDelete={canDelete}
                canReconnect={canReconnect}
                canUpdateCore={canUpdateCore}
                canReadStats={canReadStats}
              />
            </div>

            <div className="bg-muted/30 border-border/50 space-y-2.5 rounded-lg border px-3 py-2.5">
              <div className={cn('text-muted-foreground flex items-center gap-2 text-xs', dir === 'rtl' ? 'flex-row-reverse justify-end' : 'flex-row')}>
                <Link2 className="h-3.5 w-3.5 shrink-0 opacity-70" />
                <span dir="ltr" className="truncate font-mono text-[12px] sm:text-[13px]">
                  {node.address}:{node.port}
                </span>
              </div>

              {(coreVersion || node.node_version) && (
                <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
                  {coreVersion && (
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <button
                          type="button"
                          onClick={handleCoreVersionClick}
                          className={cn(
                            'inline-flex items-center gap-1.5 rounded-md px-0 text-left',
                            canUpdateCore && hasCoreUpdate && 'focus-visible:ring-ring cursor-pointer focus-visible:ring-2 focus-visible:outline-none',
                            (!canUpdateCore || !hasCoreUpdate) && 'cursor-default',
                          )}
                          aria-label={t('nodeModal.updateCore', { defaultValue: 'Update Core' })}
                        >
                          <Package className={cn('h-3.5 w-3.5 shrink-0', hasCoreUpdate ? 'text-amber-600 dark:text-amber-400' : 'text-muted-foreground')} />
                          <span className="text-muted-foreground text-[10px] tracking-wide uppercase">{t('node.xrayVersion', { defaultValue: 'Core' })}</span>
                          <span className={cn('font-mono text-xs font-medium', hasCoreUpdate ? 'text-amber-700 dark:text-amber-300' : 'text-foreground')}>{coreVersion}</span>
                          {hasCoreUpdate && <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />}
                        </button>
                      </TooltipTrigger>
                      <TooltipContent side="top" className="max-w-xs">
                        <div className="space-y-2 text-xs">
                          <div className="font-semibold">{t('node.xrayVersion', { defaultValue: 'Core' })}</div>
                          <div className="space-y-1.5">
                            <div className="flex items-center justify-between gap-4">
                              <span>{t('version.currentVersion', { defaultValue: 'Current' })}</span>
                              <span className="font-mono font-medium">{coreVersion}</span>
                            </div>
                            {isXrayBackend && latestXrayVersion && (
                              <div className="flex items-center justify-between gap-4">
                                <span>{t('version.latestVersion', { defaultValue: 'Latest' })}</span>
                                <span className="font-mono font-medium">{latestXrayVersion}</span>
                              </div>
                            )}
                            {hasCoreUpdate && (
                              <>
                                <Separator className="my-1.5" />
                                <span>{t('nodeModal.updateAvailable', { defaultValue: 'Update available' })}</span>
                              </>
                            )}
                          </div>
                        </div>
                      </TooltipContent>
                    </Tooltip>
                  )}
                  {node.node_version && (
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <div className="inline-flex items-center gap-1.5">
                          <Server className={cn('h-3.5 w-3.5 shrink-0', hasNodeVersionUpdate ? 'text-amber-600 dark:text-amber-400' : 'text-muted-foreground')} />
                          <span className="text-muted-foreground text-[10px] tracking-wide uppercase">{t('node.coreVersion', { defaultValue: 'Node' })}</span>
                          <span className={cn('font-mono text-xs font-medium', hasNodeVersionUpdate ? 'text-amber-700 dark:text-amber-300' : 'text-foreground')}>{node.node_version}</span>
                          {hasNodeVersionUpdate && <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />}
                        </div>
                      </TooltipTrigger>
                      <TooltipContent side="top" className="max-w-xs">
                        <div className="space-y-2 text-xs">
                          <div className="font-semibold">{t('node.coreVersion', { defaultValue: 'Node Core' })}</div>
                          <div className="space-y-1.5">
                            <div className="flex items-center justify-between gap-4">
                              <span>{t('version.currentVersion', { defaultValue: 'Current' })}</span>
                              <span className="font-mono font-medium">{node.node_version}</span>
                            </div>
                            {!isWireGuardCore && latestNodeVersion && (
                              <div className="flex items-center justify-between gap-4">
                                <span>{t('version.latestVersion', { defaultValue: 'Latest' })}</span>
                                <span className="font-mono font-medium">{latestNodeVersion}</span>
                              </div>
                            )}
                            {hasNodeVersionUpdate && (
                              <>
                                <Separator className="my-1.5" />
                                <span>{t('nodeModal.updateAvailable', { defaultValue: 'Update available' })}</span>
                              </>
                            )}
                          </div>
                        </div>
                      </TooltipContent>
                    </Tooltip>
                  )}
                </div>
              )}
            </div>

            {hasUsageDisplay ? <NodeUsageDisplay node={node} /> : null}
          </div>
        </div>
      </Card>
      {canUpdateCore && <UpdateCoreDialog node={node} isOpen={showUpdateCoreDialog} onOpenChange={setShowUpdateCoreDialog} />}
    </TooltipProvider>
  )
}
