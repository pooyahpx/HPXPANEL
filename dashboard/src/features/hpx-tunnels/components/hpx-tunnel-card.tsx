import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { cn } from '@/lib/utils'
import type { HpxTunnelResponse } from '@/service/api/hpx-tunnels'
import { formatBytes } from '@/utils/formatByte'
import { Activity, Globe, KeyRound, Play, RefreshCw, Shield, Square, Stethoscope, Trash2, Zap, ScrollText } from 'lucide-react'
import type { ComponentType } from 'react'
import { useTranslation } from 'react-i18next'

interface HpxTunnelCardProps {
  tunnel: HpxTunnelResponse
  onEdit: (tunnel: HpxTunnelResponse) => void
  onStart: (id: number) => void
  onStop: (id: number) => void
  onRestart: (id: number) => void
  onDelete?: (tunnel: HpxTunnelResponse) => void
  onRegenerateJoinToken?: (id: number) => void
  onDiagnoseRepair?: (id: number) => void
  onViewLogs?: (tunnel: HpxTunnelResponse) => void
  actionLoading?: boolean
  canDelete?: boolean
}

const statusTone: Record<string, string> = {
  running: 'bg-emerald-500/15 text-emerald-600 border-emerald-500/30',
  stopped: 'bg-muted text-muted-foreground border-border',
  starting: 'bg-blue-500/15 text-blue-600 border-blue-500/30',
  stopping: 'bg-amber-500/15 text-amber-600 border-amber-500/30',
  error: 'bg-destructive/15 text-destructive border-destructive/30',
  unhealthy: 'bg-orange-500/15 text-orange-600 border-orange-500/30',
  pending_claim: 'bg-violet-500/15 text-violet-600 border-violet-500/30',
}

export default function HpxTunnelCard({
  tunnel,
  onEdit,
  onStart,
  onStop,
  onRestart,
  onDelete,
  onRegenerateJoinToken,
  onDiagnoseRepair,
  onViewLogs,
  actionLoading,
  canDelete,
}: HpxTunnelCardProps) {
  const { t } = useTranslation()
  const isRunning = tunnel.status === 'running'
  const isPendingClaim = tunnel.status === 'pending_claim' || (tunnel.role === 'iran' && !tunnel.agent_claimed)
  const isIranAgent = tunnel.role === 'iran'
  const isForeignPanel = tunnel.role === 'foreign'

  return (
    <Card className="overflow-hidden border-border/70 bg-gradient-to-br from-card via-card to-muted/20 p-0 shadow-sm">
      <div className="border-b border-border/60 bg-muted/20 px-4 py-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="truncate text-base font-semibold">{tunnel.name}</h3>
              <Badge variant="outline" className={cn('text-xs capitalize', statusTone[tunnel.status])}>
                {t(`hpxTunnel.status.${tunnel.status}`, { defaultValue: tunnel.status })}
              </Badge>
              <Badge variant="secondary" className="text-xs uppercase">
                {tunnel.role === 'iran' ? t('hpxTunnel.role.iran', { defaultValue: 'IRAN' }) : t('hpxTunnel.role.foreign', { defaultValue: 'FOREIGN' })}
              </Badge>
              {tunnel.auto_heal_enabled !== false && (
                <Badge variant="outline" className="text-xs">
                  {t('hpxTunnel.autoHealOn', { defaultValue: 'Auto-heal on' })}
                </Badge>
              )}
              {isIranAgent && tunnel.agent_claimed && (
                <Badge variant="outline" className="text-xs">
                  {t('hpxTunnel.agent.claimed', { defaultValue: 'Agent claimed' })}
                </Badge>
              )}
            </div>
            <p className="text-muted-foreground mt-1 text-xs">
              {tunnel.role === 'iran'
                ? t('hpxTunnel.remoteTarget', { ip: tunnel.remote_ip || '—', defaultValue: 'Remote: {{ip}}' })
                : t('hpxTunnel.listenTarget', { addr: tunnel.server_listen, defaultValue: 'Listen: {{addr}}' })}
              {tunnel.agent_host ? ` · ${tunnel.agent_host}` : ''}
            </p>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {onDiagnoseRepair && (
              <Button size="sm" variant="secondary" disabled={actionLoading} onClick={() => onDiagnoseRepair(tunnel.id)}>
                <Stethoscope className="size-3.5" />
                {t('hpxTunnel.diagnoseRepair', { defaultValue: 'Diagnose & Repair' })}
              </Button>
            )}
            {isForeignPanel && onViewLogs && (
              <Button size="sm" variant="outline" disabled={actionLoading} onClick={() => onViewLogs(tunnel)}>
                <ScrollText className="size-3.5" />
                {t('hpxTunnel.viewLogs', { defaultValue: 'View logs' })}
              </Button>
            )}
            {isIranAgent && onRegenerateJoinToken && (
              <Button size="sm" variant="secondary" disabled={actionLoading} onClick={() => onRegenerateJoinToken(tunnel.id)}>
                <KeyRound className="size-3.5" />
                {t('hpxTunnel.agent.regenerateToken', { defaultValue: 'Join token' })}
              </Button>
            )}
            {!isPendingClaim && (
              <>
                {!isRunning ? (
                  <Button size="sm" variant="default" disabled={actionLoading} onClick={() => onStart(tunnel.id)}>
                    <Play className="size-3.5" />
                    {t('hpxTunnel.start', { defaultValue: 'Start' })}
                  </Button>
                ) : (
                  <Button size="sm" variant="outline" disabled={actionLoading} onClick={() => onStop(tunnel.id)}>
                    <Square className="size-3.5" />
                    {t('hpxTunnel.stop', { defaultValue: 'Stop' })}
                  </Button>
                )}
                <Button size="sm" variant="outline" disabled={actionLoading} onClick={() => onRestart(tunnel.id)}>
                  <RefreshCw className="size-3.5" />
                  {t('hpxTunnel.restart', { defaultValue: 'Restart' })}
                </Button>
              </>
            )}
            <Button size="sm" variant="ghost" onClick={() => onEdit(tunnel)}>
              {t('edit', { defaultValue: 'Edit' })}
            </Button>
            {canDelete && onDelete && (
              <Button size="sm" variant="ghost" className="text-destructive hover:text-destructive" disabled={actionLoading} onClick={() => onDelete(tunnel)}>
                <Trash2 className="size-3.5" />
                {t('delete', { defaultValue: 'Delete' })}
              </Button>
            )}
          </div>
        </div>
      </div>

      {isPendingClaim && (
        <div className="border-b border-violet-500/20 bg-violet-500/5 px-4 py-3 text-sm">
          <p className="font-medium text-violet-700 dark:text-violet-300">
            {t('hpxTunnel.agent.waitingClaim', { defaultValue: 'Waiting for Iran agent…' })}
          </p>
          <p className="text-muted-foreground mt-1 text-xs">
            {t('hpxTunnel.agent.waitingClaimHint', {
              defaultValue: 'Generate/copy the join token and run it on the Iran VPS. The panel will not run Docker for IRAN tunnels.',
            })}
          </p>
        </div>
      )}

      <div className="grid gap-3 p-4 sm:grid-cols-2 xl:grid-cols-4">
        <Metric icon={Activity} label={t('hpxTunnel.latency', { defaultValue: 'Latency' })} value={tunnel.latency_ms != null ? `${tunnel.latency_ms.toFixed(1)} ms` : '—'} />
        <Metric
          icon={Zap}
          label={t('hpxTunnel.packetLoss', { defaultValue: 'Packet loss' })}
          value={tunnel.packet_loss_pct != null ? `${tunnel.packet_loss_pct.toFixed(0)}%` : '—'}
          tone={tunnel.packet_loss_pct != null && tunnel.packet_loss_pct > 10 ? 'danger' : undefined}
        />
        <Metric icon={Globe} label={t('hpxTunnel.interface', { defaultValue: 'Interface' })} value={`${tunnel.interface} · ${tunnel.local_ip}`} mono />
        <Metric icon={Shield} label={t('hpxTunnel.traffic', { defaultValue: 'Traffic' })} value={`↑ ${formatBytes(tunnel.bytes_up)} · ↓ ${formatBytes(tunnel.bytes_down)}`} />
      </div>

      {(tunnel.auto_failover || tunnel.message || tunnel.agent_last_seen || tunnel.last_heal_action) && (
        <div className="border-t border-border/60 px-4 py-3 text-xs">
          {tunnel.auto_failover && (
            <Badge variant="outline" className="me-2">
              {t('hpxTunnel.failoverEnabled', { defaultValue: 'Auto-failover' })}
            </Badge>
          )}
          {tunnel.last_heal_action && (
            <span className="text-muted-foreground me-2">
              {t('hpxTunnel.lastHeal', { defaultValue: 'Last repair: {{action}}', action: tunnel.last_heal_action })}
            </span>
          )}
          {tunnel.agent_last_seen && (
            <span className="text-muted-foreground me-2">
              {t('hpxTunnel.agent.lastSeen', {
                defaultValue: 'Agent last seen: {{when}}',
                when: new Date(tunnel.agent_last_seen).toLocaleString(),
              })}
            </span>
          )}
          {tunnel.message && <span className="text-muted-foreground">{tunnel.message}</span>}
        </div>
      )}
    </Card>
  )
}

function Metric({
  icon: Icon,
  label,
  value,
  mono,
  tone,
}: {
  icon: ComponentType<{ className?: string }>
  label: string
  value: string
  mono?: boolean
  tone?: 'danger'
}) {
  return (
    <div className={cn('rounded-lg border bg-background/60 px-3 py-2.5', tone === 'danger' && 'border-destructive/30 bg-destructive/5')}>
      <div className="text-muted-foreground flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide">
        <Icon className="size-3.5" />
        {label}
      </div>
      <div className={cn('mt-1 truncate text-sm font-semibold', mono && 'font-mono')} title={value}>
        {value}
      </div>
    </div>
  )
}

export function HpxTunnelLogsDialog({
  open,
  onOpenChange,
  tunnel,
  logs,
  loading,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  tunnel: HpxTunnelResponse | null
  logs: string
  loading?: boolean
}) {
  const { t } = useTranslation()
  if (!tunnel) return null
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{t('hpxTunnel.logsTitle', { defaultValue: 'Tunnel logs' })} — {tunnel.name}</DialogTitle>
          <DialogDescription>{t('hpxTunnel.logsDescription', { defaultValue: 'Recent Docker container output (FOREIGN on panel host).' })}</DialogDescription>
        </DialogHeader>
        <pre className="bg-muted/40 max-h-[60vh] overflow-auto rounded-md border p-3 font-mono text-[11px] leading-relaxed whitespace-pre-wrap" dir="ltr">
          {loading ? t('loading', { defaultValue: 'Loading…' }) : logs || '—'}
        </pre>
      </DialogContent>
    </Dialog>
  )
}
