import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import HpxPulseWizard from '@/features/hpx-pulse/wizard/hpx-pulse-wizard'
import {
  useDeleteHpxPulse,
  useGetHpxPulses,
  useRegeneratePulseTokens,
  type HpxPulseResponse,
} from '@/service/api/hpx-pulse'
import { useAdmin } from '@/hooks/use-admin'
import { hasPermission } from '@/utils/rbac'
import { cn } from '@/lib/utils'
import { Activity, Copy, Plus, RefreshCw, Trash2, Zap } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

const statusTone: Record<string, string> = {
  running: 'bg-emerald-500/15 text-emerald-600 border-emerald-500/40 dark:text-emerald-400',
  starting: 'bg-blue-500/15 text-blue-600 border-blue-500/40',
  partial: 'bg-amber-500/15 text-amber-600 border-amber-500/40',
  pending_claim: 'bg-violet-500/15 text-violet-600 border-violet-500/40',
  stopped: 'bg-muted text-muted-foreground border-border',
  error: 'bg-destructive/15 text-destructive border-destructive/40',
  unhealthy: 'bg-orange-500/15 text-orange-600 border-orange-500/40',
}

function carrierLabel(carrier: string | null, t: (k: string, o?: { defaultValue: string }) => string) {
  if (carrier === 'pck') return t('hpxPulse.carrierTcpStealth', { defaultValue: 'TCP Stealth' })
  if (carrier === 'udp') return t('hpxPulse.carrierUdp', { defaultValue: 'UDP' })
  if (carrier === 'xdi') return t('hpxPulse.carrierIcmp', { defaultValue: 'ICMP' })
  return carrier || '—'
}

function PulseCard({
  pulse,
  onDelete,
  onRegenerate,
}: {
  pulse: HpxPulseResponse
  onDelete: () => void
  onRegenerate: () => void
}) {
  const { t, i18n } = useTranslation()
  const fa = i18n.language?.startsWith('fa')
  const top = pulse.advice?.profiles.find(p => p.profile_id === pulse.profile_id)
  const isRunning = pulse.status === 'running'
  const bothAgents = pulse.iran_claimed && pulse.abroad_claimed

  return (
    <Card
      className={cn(
        'space-y-3 p-4 transition-colors',
        isRunning && 'border-emerald-500/50 bg-emerald-500/5 shadow-emerald-500/10 shadow-sm',
        bothAgents && !isRunning && 'border-amber-500/40 bg-amber-500/5',
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <Zap className={cn('size-4', isRunning ? 'text-emerald-500' : 'text-primary')} />
            <span className="font-semibold">{pulse.name}</span>
            <Badge variant="outline" className={cn('text-xs capitalize', statusTone[pulse.status])}>
              {t(`hpxPulse.status.${pulse.status}`, { defaultValue: pulse.status })}
            </Badge>
            <Badge variant="secondary" className="text-xs uppercase">
              {carrierLabel(pulse.carrier, t)}
            </Badge>
          </div>
          <p className="text-muted-foreground mt-1 text-xs">
            HPX Direct · {pulse.profile_id} · {pulse.preset}
          </p>
        </div>
        <div className="flex gap-1">
          <Button size="sm" variant="outline" onClick={onRegenerate}>
            {t('hpxPulse.regenerate', { defaultValue: 'Tokens' })}
          </Button>
          <Button size="sm" variant="destructive" onClick={onDelete}>
            <Trash2 className="size-3.5" />
          </Button>
        </div>
      </div>

      <div className="grid gap-2 text-xs sm:grid-cols-3">
        <div className={cn('rounded-md border px-2 py-1.5', pulse.iran_claimed ? 'border-emerald-500/40 bg-emerald-500/5' : 'border-border')}>
          <span className="text-muted-foreground block">{t('hpxPulse.iranAgent', { defaultValue: 'Iran agent' })}</span>
          <span className={pulse.iran_claimed ? 'text-emerald-600 dark:text-emerald-400' : ''}>
            {pulse.iran_claimed
              ? t('hpxPulse.agentConnected', { defaultValue: 'connected' })
              : t('hpxPulse.agentWaiting', { defaultValue: 'waiting' })}
          </span>
        </div>
        <div className={cn('rounded-md border px-2 py-1.5', pulse.abroad_claimed ? 'border-emerald-500/40 bg-emerald-500/5' : 'border-border')}>
          <span className="text-muted-foreground block">{t('hpxPulse.abroadAgent', { defaultValue: 'Abroad agent' })}</span>
          <span className={pulse.abroad_claimed ? 'text-emerald-600 dark:text-emerald-400' : ''}>
            {pulse.abroad_claimed
              ? t('hpxPulse.agentConnected', { defaultValue: 'connected' })
              : t('hpxPulse.agentWaiting', { defaultValue: 'waiting' })}
          </span>
        </div>
        <div className={cn('rounded-md border px-2 py-1.5', isRunning ? 'border-emerald-500/40 bg-emerald-500/5' : 'border-border')}>
          <span className="text-muted-foreground flex items-center gap-1">
            <Activity className="size-3" />
            {t('hpxPulse.ping', { defaultValue: 'Ping' })}
          </span>
          <span className={isRunning && pulse.latency_ms != null ? 'font-medium text-emerald-600 dark:text-emerald-400' : ''}>
            {pulse.latency_ms != null ? `${pulse.latency_ms.toFixed(1)} ms` : '—'}
          </span>
        </div>
      </div>

      <div className="text-muted-foreground grid gap-1 text-xs sm:grid-cols-2">
        <span>{t('hpxPulse.tunnelPort', { defaultValue: 'Tunnel port' })}: {pulse.control_port}</span>
        {pulse.port_forwards?.length ? (
          <span>{t('hpxPulse.portForwards', { defaultValue: 'Port forwards' })}: {pulse.port_forwards.join(', ')}</span>
        ) : null}
      </div>
      {top && (
        <p className="text-xs">{fa ? top.title_fa : top.title}</p>
      )}
      {pulse.message && <p className="text-muted-foreground text-xs">{pulse.message}</p>}
    </Card>
  )
}

export default function HpxPulseList() {
  const { t } = useTranslation()
  const { admin } = useAdmin()
  const canCreate = hasPermission(admin, 'hpx_pulse', 'create')
  const canDelete = hasPermission(admin, 'hpx_pulse', 'delete')
  const { data, isLoading, isError, error, refetch, isFetching } = useGetHpxPulses({ limit: 50, offset: 0 })
  const deleteMutation = useDeleteHpxPulse()
  const regenMutation = useRegeneratePulseTokens()
  const [wizardOpen, setWizardOpen] = useState(false)
  const [joinCommands, setJoinCommands] = useState<{ iran?: string; abroad?: string } | null>(null)

  useEffect(() => {
    const handler = () => setWizardOpen(true)
    window.addEventListener('openHpxPulseDialog', handler)
    return () => window.removeEventListener('openHpxPulseDialog', handler)
  }, [])

  const copy = async (text: string) => {
    await navigator.clipboard.writeText(text)
    toast.success(t('copied', { defaultValue: 'Copied' }))
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-muted-foreground text-sm">
          {t('hpxPulse.summary', {
            defaultValue: '{{total}} pulse tunnel(s)',
            total: data?.total ?? 0,
          })}
        </p>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
            <RefreshCw className={`size-3.5 ${isFetching ? 'animate-spin' : ''}`} />
          </Button>
          {canCreate && (
            <Button size="sm" onClick={() => setWizardOpen(true)}>
              <Plus className="size-3.5" />
              {t('hpxPulse.add', { defaultValue: 'New Pulse' })}
            </Button>
          )}
        </div>
      </div>

      {isError && (
        <Card className="border-destructive/50 bg-destructive/5 space-y-1 p-4 text-sm">
          <p className="font-medium text-destructive">
            {t('hpxPulse.loadError', { defaultValue: 'Could not load Pulse tunnels from panel API' })}
          </p>
          <p className="text-muted-foreground text-xs">
            {t('hpxPulse.loadErrorHint', {
              defaultValue: 'Update panel to v3.7.2+, run DB migration (alembic upgrade head), and check hpx_pulse permissions.',
            })}
          </p>
          {(error as Error)?.message && (
            <p className="text-muted-foreground font-mono text-[11px]">{(error as Error).message}</p>
          )}
        </Card>
      )}

      {joinCommands && (
        <Card className="space-y-2 p-4 text-xs">
          <p className="font-medium">{t('hpxPulse.installCommands', { defaultValue: 'Install commands' })}</p>
          <p className="text-muted-foreground text-[11px]">
            {t('hpxPulse.panelUrlWarning', {
              defaultValue: 'Use the exact panel URL below on both servers — a typo (e.g. duolingoo vs duolingo) means agents join a different panel than this UI.',
            })}
          </p>
          {joinCommands.iran && (
            <div className="space-y-1">
              <span className="text-muted-foreground">Iran</span>
              <pre className="bg-muted overflow-x-auto rounded p-2 font-mono text-[11px]">{joinCommands.iran}</pre>
              <Button size="sm" variant="secondary" onClick={() => copy(joinCommands.iran!)}>
                <Copy className="size-3" /> Iran
              </Button>
            </div>
          )}
          {joinCommands.abroad && (
            <div className="space-y-1">
              <span className="text-muted-foreground">Abroad</span>
              <pre className="bg-muted overflow-x-auto rounded p-2 font-mono text-[11px]">{joinCommands.abroad}</pre>
              <Button size="sm" variant="secondary" onClick={() => copy(joinCommands.abroad!)}>
                <Copy className="size-3" /> Abroad
              </Button>
            </div>
          )}
        </Card>
      )}

      {isLoading ? (
        <Skeleton className="h-32 w-full" />
      ) : isError ? null : (data?.pulses?.length ?? 0) === 0 ? (
        <Card className="text-muted-foreground p-8 text-center text-sm">
          {t('hpxPulse.empty', { defaultValue: 'No Pulse tunnels yet. Create one with the advisor wizard.' })}
        </Card>
      ) : (
        <div className="grid gap-3 lg:grid-cols-2">
          {data!.pulses.map(pulse => (
            <PulseCard
              key={pulse.id}
              pulse={pulse}
              onDelete={
                canDelete
                  ? async () => {
                      await deleteMutation.mutateAsync(pulse.id)
                      toast.success(t('deleted', { defaultValue: 'Deleted' }))
                    }
                  : () => {}
              }
              onRegenerate={async () => {
                const res = await regenMutation.mutateAsync(pulse.id)
                setJoinCommands({ iran: res.iran_join_command ?? undefined, abroad: res.abroad_join_command ?? undefined })
              }}
            />
          ))}
        </div>
      )}

      <HpxPulseWizard
        open={wizardOpen}
        onOpenChange={setWizardOpen}
        onCreated={res => {
          setJoinCommands({
            iran: res.iran_join_command ?? undefined,
            abroad: res.abroad_join_command ?? undefined,
          })
          refetch()
        }}
      />
    </div>
  )
}
