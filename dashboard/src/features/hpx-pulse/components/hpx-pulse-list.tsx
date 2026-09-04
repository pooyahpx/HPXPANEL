import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Skeleton } from '@/components/ui/skeleton'
import HpxPulseWizard from '@/features/hpx-pulse/wizard/hpx-pulse-wizard'
import {
  useDeleteHpxPulse,
  useGetHpxPulses,
  useRegeneratePulseTokens,
  useSyncHpxPulse,
  useUpdateHpxPulse,
  type HpxPulseResponse,
} from '@/service/api/hpx-pulse'
import { useAdmin } from '@/hooks/use-admin'
import { hasPermission } from '@/utils/rbac'
import { cn } from '@/lib/utils'
import {
  Activity,
  Copy,
  KeyRound,
  Pencil,
  Plus,
  RefreshCw,
  Save,
  Timer,
  Trash2,
  Zap,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

type JoinCommandSet = {
  iran?: string
  iranAlt?: string
  abroad?: string
  abroadAlt?: string
}

function JoinCommandBlock({
  label,
  primary,
  alt,
  primaryHint,
  onCopy,
  t,
}: {
  label: string
  primary: string
  alt?: string
  primaryHint?: string
  onCopy: (text: string, key: string) => void
  t: (k: string, o?: { defaultValue: string }) => string
}) {
  const hint =
    primaryHint ??
    t('hpxPulse.joinCommandPrimaryGithub', { defaultValue: 'Recommended (GitHub)' })
  return (
    <div className="space-y-2">
      <span className="text-muted-foreground text-sm font-medium">{label}</span>
      <div className="space-y-1.5">
        <p className="text-[10px] font-medium uppercase tracking-wide text-emerald-600 dark:text-emerald-400">
          {hint}
        </p>
        <pre className="bg-muted/80 overflow-x-auto rounded-lg border p-3 font-mono text-[11px] leading-relaxed">
          {primary}
        </pre>
        <Button size="sm" variant="secondary" className="h-8 gap-1.5" onClick={() => onCopy(primary, label)}>
          <Copy className="size-3" /> {label}
        </Button>
      </div>
      {alt ? (
        <div className="space-y-1.5">
          <p className="text-muted-foreground text-[10px] font-medium uppercase tracking-wide">
            {t('hpxPulse.joinCommandAltPanel', { defaultValue: 'Alternative (panel URL)' })}
          </p>
          <pre className="bg-muted/60 overflow-x-auto rounded-lg border border-dashed p-3 font-mono text-[11px] leading-relaxed">
            {alt}
          </pre>
          <Button size="sm" variant="outline" className="h-8 gap-1.5" onClick={() => onCopy(alt, `${label} alt`)}>
            <Copy className="size-3" /> {label} (panel)
          </Button>
        </div>
      ) : null}
    </div>
  )
}

const statusTone: Record<string, string> = {
  running: 'bg-emerald-500/15 text-emerald-700 border-emerald-500/35 dark:text-emerald-400',
  starting: 'bg-sky-500/15 text-sky-700 border-sky-500/35 dark:text-sky-400',
  partial: 'bg-amber-500/15 text-amber-700 border-amber-500/35 dark:text-amber-400',
  pending_claim: 'bg-violet-500/15 text-violet-700 border-violet-500/35 dark:text-violet-400',
  stopped: 'bg-muted text-muted-foreground border-border',
  error: 'bg-destructive/15 text-destructive border-destructive/35',
  unhealthy: 'bg-orange-500/15 text-orange-700 border-orange-500/35 dark:text-orange-400',
}

function carrierLabel(carrier: string | null, t: (k: string, o?: { defaultValue: string }) => string) {
  if (carrier === 'stealth') return t('hpxPulse.carrierStealth', { defaultValue: 'STEALTH' })
  if (carrier === 'pck') return t('hpxPulse.carrierPck', { defaultValue: 'PCK' })
  if (carrier === 'tcp') return t('hpxPulse.carrierTcp', { defaultValue: 'TCP' })
  if (carrier === 'tcpmux') return t('hpxPulse.carrierTcpMux', { defaultValue: 'TCP MUX' })
  if (carrier === 'udp') return t('hpxPulse.carrierUdp', { defaultValue: 'UDP' })
  if (carrier === 'kcp') return t('hpxPulse.carrierKcp', { defaultValue: 'KCP' })
  if (carrier === 'quic') return t('hpxPulse.carrierQuic', { defaultValue: 'QUIC' })
  if (carrier === 'ws') return t('hpxPulse.carrierWs', { defaultValue: 'WS' })
  if (carrier === 'wss') return t('hpxPulse.carrierWss', { defaultValue: 'WSS' })
  if (carrier === 'wssmux') return t('hpxPulse.carrierWssMux', { defaultValue: 'WSS MUX' })
  if (carrier === 'xdi') return t('hpxPulse.carrierIcmp', { defaultValue: 'ICMP' })
  return carrier?.toUpperCase() || '—'
}

function modeLabel(tunnelMode: string, t: (k: string, o?: { defaultValue: string }) => string) {
  if (tunnelMode.startsWith('reverse_')) {
    return t('hpxPulse.modeReverse', { defaultValue: 'REVERSE' })
  }
  return t('hpxPulse.modeDirect', { defaultValue: 'DIRECT' })
}

function formatAutoRestart(minutes: number | null | undefined, t: (k: string, o?: Record<string, unknown>) => string) {
  if (!minutes || minutes < 1) return null
  if (minutes < 60) {
    return t('hpxPulse.autoRestartEveryMinutes', { defaultValue: 'Every {{n}} min', n: minutes })
  }
  if (minutes % 60 === 0) {
    const hours = minutes / 60
    return t('hpxPulse.autoRestartEveryHours', { defaultValue: 'Every {{n}}h', n: hours })
  }
  return t('hpxPulse.autoRestartEveryMinutes', { defaultValue: 'Every {{n}} min', n: minutes })
}

function AgentCell({
  label,
  connected,
  host,
  t,
}: {
  label: string
  connected: boolean
  host?: string | null
  t: (k: string, o?: { defaultValue: string }) => string
}) {
  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-xl border px-3 py-2.5',
        connected
          ? 'border-emerald-500/30 bg-gradient-to-br from-emerald-500/10 to-transparent'
          : 'border-border/70 bg-muted/30',
      )}
    >
      <div className="flex items-center gap-2">
        <span
          className={cn(
            'size-2 shrink-0 rounded-full',
            connected ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.7)]' : 'bg-muted-foreground/40',
          )}
        />
        <span className="text-muted-foreground text-[11px] font-medium tracking-wide uppercase">{label}</span>
      </div>
      <p className={cn('mt-1 text-sm font-medium', connected && 'text-emerald-700 dark:text-emerald-400')}>
        {connected
          ? t('hpxPulse.agentConnected', { defaultValue: 'connected' })
          : t('hpxPulse.agentWaiting', { defaultValue: 'waiting' })}
      </p>
      {host ? (
        <p className="text-muted-foreground mt-0.5 truncate font-mono text-[10px]" dir="ltr" title={host}>
          {host}
        </p>
      ) : null}
    </div>
  )
}

const AUTO_SYNC_PRESETS = [0, 15, 30, 60, 360, 720, 1440] as const

function AutoSyncControl({
  pulse,
  disabled,
  onSave,
}: {
  pulse: HpxPulseResponse
  disabled: boolean
  onSave: (minutes: number) => Promise<void>
}) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const [minutes, setMinutes] = useState(pulse.auto_restart_interval_minutes ?? 0)
  const [saving, setSaving] = useState(false)
  const active = Boolean(pulse.auto_restart_interval_minutes)

  useEffect(() => {
    if (!open) setMinutes(pulse.auto_restart_interval_minutes ?? 0)
  }, [open, pulse.auto_restart_interval_minutes])

  const save = async (value = minutes) => {
    setSaving(true)
    try {
      await onSave(value)
      setOpen(false)
    } finally {
      setSaving(false)
    }
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          size="sm"
          variant={active ? 'secondary' : 'outline'}
          className={cn(
            'h-8 gap-1.5',
            active && 'border-sky-500/30 bg-sky-500/10 text-sky-700 hover:bg-sky-500/15 dark:text-sky-400',
          )}
          disabled={disabled}
        >
          <Timer className="size-3.5" />
          <span>{t('hpxPulse.autoSync', { defaultValue: 'Auto sync' })}</span>
          {active && (
            <span className="rounded bg-sky-500/15 px-1 text-[10px]">
              {formatAutoRestart(pulse.auto_restart_interval_minutes, t)}
            </span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80 space-y-4">
        <div className="space-y-1">
          <p className="flex items-center gap-2 text-sm font-semibold">
            <Timer className="size-4 text-sky-500" />
            {t('hpxPulse.autoSyncTitle', { defaultValue: 'Automatic tunnel sync' })}
          </p>
          <p className="text-muted-foreground text-xs leading-relaxed">
            {t('hpxPulse.autoSyncDescription', {
              defaultValue: 'Restart and refresh both connected agents on a fixed schedule.',
            })}
          </p>
        </div>

        <div className="grid grid-cols-4 gap-2">
          {AUTO_SYNC_PRESETS.map(value => (
            <Button
              key={value}
              type="button"
              size="sm"
              variant={minutes === value ? 'default' : 'outline'}
              className="h-9 px-2 text-xs"
              onClick={() => setMinutes(value)}
            >
              {value === 0
                ? t('hpxPulse.autoRestartOff', { defaultValue: 'Off' })
                : value < 60
                  ? `${value}m`
                  : `${value / 60}h`}
            </Button>
          ))}
          <Button
            type="button"
            size="sm"
            variant={!AUTO_SYNC_PRESETS.includes(minutes as (typeof AUTO_SYNC_PRESETS)[number]) ? 'default' : 'outline'}
            className="h-9 px-2 text-xs"
            onClick={() => setMinutes(45)}
          >
            {t('hpxPulse.custom', { defaultValue: 'Custom' })}
          </Button>
        </div>

        {!AUTO_SYNC_PRESETS.includes(minutes as (typeof AUTO_SYNC_PRESETS)[number]) && (
          <div className="space-y-1.5">
            <label htmlFor={`pulse-auto-sync-${pulse.id}`} className="text-xs font-medium">
              {t('hpxPulse.minutes', { defaultValue: 'Minutes' })}
            </label>
            <Input
              id={`pulse-auto-sync-${pulse.id}`}
              type="number"
              min={1}
              max={10080}
              value={minutes}
              dir="ltr"
              onChange={event => setMinutes(Math.max(1, Math.min(10080, Number(event.target.value) || 1)))}
            />
          </div>
        )}

        <div className="flex items-center justify-between gap-2 border-t pt-3">
          <span className="text-muted-foreground text-[11px]">
            {minutes > 0
              ? formatAutoRestart(minutes, t)
              : t('hpxPulse.autoSyncDisabled', { defaultValue: 'Automatic sync is disabled' })}
          </span>
          <Button size="sm" className="h-8 gap-1.5" disabled={saving} onClick={() => void save()}>
            {saving ? <RefreshCw className="size-3.5 animate-spin" /> : <Save className="size-3.5" />}
            {t('save', { defaultValue: 'Save' })}
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  )
}

function PulseCard({
  pulse,
  onDelete,
  onRegenerate,
  onSync,
  onAutoSync,
  onEdit,
  canUpdate,
  canDelete,
  syncLoading,
}: {
  pulse: HpxPulseResponse
  onDelete: () => void
  onRegenerate: () => void
  onSync: () => void
  onAutoSync: (minutes: number) => Promise<void>
  onEdit: () => void
  canUpdate: boolean
  canDelete: boolean
  syncLoading: boolean
}) {
  const { t, i18n } = useTranslation()
  const fa = i18n.language?.startsWith('fa')
  const top = pulse.advice?.profiles.find(p => p.profile_id === pulse.profile_id)
  const isRunning = pulse.status === 'running'
  const bothAgents = pulse.iran_claimed && pulse.abroad_claimed
  const autoLabel = formatAutoRestart(pulse.auto_restart_interval_minutes, t)

  return (
    <Card
      className={cn(
        'group relative overflow-hidden border transition-all duration-300',
        isRunning && 'border-emerald-500/40 shadow-[0_0_0_1px_rgba(16,185,129,0.08)]',
        bothAgents && !isRunning && 'border-amber-500/35',
        !isRunning && !bothAgents && 'border-border/80',
      )}
    >
      <div
        className={cn(
          'pointer-events-none absolute inset-x-0 top-0 h-1',
          isRunning && 'bg-gradient-to-r from-emerald-500 via-teal-400 to-emerald-500',
          pulse.status === 'partial' && 'bg-gradient-to-r from-amber-400 to-orange-400',
          pulse.status === 'pending_claim' && 'bg-gradient-to-r from-violet-400 to-fuchsia-400',
          (pulse.status === 'error' || pulse.status === 'unhealthy') && 'bg-gradient-to-r from-red-500 to-orange-500',
          pulse.status === 'stopped' && 'bg-muted-foreground/30',
        )}
      />

      <div className="space-y-4 p-4 pt-5 sm:p-5 sm:pt-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <div
                className={cn(
                  'flex size-8 items-center justify-center rounded-lg',
                  isRunning ? 'bg-emerald-500/15 text-emerald-500' : 'bg-primary/10 text-primary',
                )}
              >
                <Zap className={cn('size-4', isRunning && 'animate-pulse')} />
              </div>
              <h3 className="truncate text-base font-semibold tracking-tight" dir="ltr">
                {pulse.name}
              </h3>
              <Badge variant="outline" className={cn('h-6 text-[11px] capitalize', statusTone[pulse.status])}>
                {t(`hpxPulse.status.${pulse.status}`, { defaultValue: pulse.status })}
              </Badge>
            </div>
            <div className="flex flex-wrap items-center gap-1.5">
              <Badge variant="secondary" className="h-5 rounded-md px-1.5 text-[10px] font-medium tracking-wide uppercase">
                {modeLabel(pulse.tunnel_mode, t)}
              </Badge>
              <Badge variant="secondary" className="h-5 rounded-md px-1.5 text-[10px] font-medium tracking-wide uppercase">
                {carrierLabel(pulse.carrier, t)}
              </Badge>
              <span className="text-muted-foreground text-[11px]">
                {pulse.tunnel_mode.startsWith('reverse_') ? 'HPX Reverse' : 'HPX Direct'} · {pulse.preset}
              </span>
              {autoLabel && (
                <Badge
                  variant="outline"
                  className="h-5 gap-1 rounded-md border-sky-500/30 bg-sky-500/10 px-1.5 text-[10px] text-sky-700 dark:text-sky-400"
                >
                  <Timer className="size-3" />
                  {autoLabel}
                </Badge>
              )}
            </div>
          </div>

          <div className="flex flex-wrap gap-1">
            {canUpdate && (pulse.iran_claimed || pulse.abroad_claimed) && (
              <Button size="sm" variant="outline" className="h-8 gap-1.5" onClick={onSync} disabled={syncLoading}>
                <RefreshCw className={cn('size-3.5', syncLoading && 'animate-spin')} />
                {t('hpxPulse.sync', { defaultValue: 'Sync' })}
              </Button>
            )}
            {canUpdate && <AutoSyncControl pulse={pulse} disabled={syncLoading} onSave={onAutoSync} />}
            {canUpdate && (
              <Button size="sm" variant="outline" className="h-8 gap-1.5" onClick={onEdit}>
                <Pencil className="size-3.5" />
                {t('edit', { defaultValue: 'Edit' })}
              </Button>
            )}
            {canUpdate && (
              <Button size="sm" variant="outline" className="h-8 gap-1.5" onClick={onRegenerate}>
                <KeyRound className="size-3.5" />
                {t('hpxPulse.regenerate', { defaultValue: 'Tokens' })}
              </Button>
            )}
            {canDelete && (
              <Button
                size="sm"
                variant="ghost"
                className="text-destructive hover:bg-destructive/10 h-8 w-8 p-0"
                title={t('delete', { defaultValue: 'Delete' })}
                onClick={onDelete}
              >
                <Trash2 className="size-3.5" />
              </Button>
            )}
          </div>
        </div>

        <div className="relative grid gap-2 sm:grid-cols-[1fr_auto_1fr_auto] sm:items-center">
          <AgentCell
            label={t('hpxPulse.iranAgent', { defaultValue: 'Iran agent' })}
            connected={pulse.iran_claimed}
            host={pulse.iran_agent_host}
            t={t}
          />
          <div className="text-muted-foreground hidden items-center gap-1 sm:flex">
            <span className="bg-border h-px w-3" />
            <Zap className={cn('size-3.5', isRunning && 'text-emerald-500')} />
            <span className="bg-border h-px w-3" />
          </div>
          <AgentCell
            label={t('hpxPulse.abroadAgent', { defaultValue: 'Abroad agent' })}
            connected={pulse.abroad_claimed}
            host={pulse.abroad_agent_host}
            t={t}
          />
          <div
            className={cn(
              'relative overflow-hidden rounded-xl border px-3 py-2.5 sm:min-w-28',
              pulse.latency_ms != null && pulse.status === 'running'
                ? 'border-emerald-500/30 bg-gradient-to-br from-emerald-500/10 to-transparent'
                : pulse.status === 'unhealthy'
                  ? 'border-orange-500/30 bg-orange-500/5'
                  : 'border-border/70 bg-muted/30',
            )}
          >
            <div className="text-muted-foreground flex items-center gap-1.5 text-[11px] font-medium tracking-wide uppercase">
              <Activity className={cn('size-3', pulse.latency_ms != null && 'animate-pulse')} />
              {t('hpxPulse.ping', { defaultValue: 'Ping' })}
              {pulse.latency_ms != null && (
                <span className="rounded bg-emerald-500/15 px-1 text-[9px] text-emerald-600 dark:text-emerald-400">
                  {t('hpxPulse.live', { defaultValue: 'live' })}
                </span>
              )}
            </div>
            <p
              className={cn(
                'mt-1 text-sm font-semibold tabular-nums',
                pulse.latency_ms != null && pulse.status === 'running' && 'text-emerald-700 dark:text-emerald-400',
                pulse.status === 'unhealthy' && 'text-orange-600 dark:text-orange-400',
              )}
              dir="ltr"
            >
              {pulse.latency_ms != null ? `${pulse.latency_ms.toFixed(1)} ms` : '—'}
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t pt-3 text-xs">
          <span className="text-muted-foreground">
            {t('hpxPulse.tunnelPort', { defaultValue: 'Tunnel port' })}:{' '}
            <span className="text-foreground font-mono font-medium" dir="ltr">
              {pulse.control_port}
            </span>
          </span>
          {pulse.port_forwards?.length ? (
            <span className="text-muted-foreground">
              {t('hpxPulse.portForwards', { defaultValue: 'Port forwards' })}:{' '}
              <span className="text-foreground font-mono font-medium" dir="ltr">
                {pulse.port_forwards.join(', ')}
              </span>
            </span>
          ) : null}
        </div>

        {(top || pulse.message) && (
          <div className="space-y-1">
            {top && <p className="text-foreground/80 text-xs">{fa ? top.title_fa : top.title}</p>}
            {pulse.message && <p className="text-muted-foreground text-xs leading-relaxed">{pulse.message}</p>}
          </div>
        )}
      </div>
    </Card>
  )
}

export default function HpxPulseList() {
  const { t } = useTranslation()
  const { admin } = useAdmin()
  const canCreate = hasPermission(admin, 'hpx_pulse', 'create')
  const canUpdate = hasPermission(admin, 'hpx_pulse', 'update')
  const canDelete = hasPermission(admin, 'hpx_pulse', 'delete')
  const { data, isLoading, isError, error, refetch, isFetching } = useGetHpxPulses({ limit: 50, offset: 0 })
  const deleteMutation = useDeleteHpxPulse()
  const regenMutation = useRegeneratePulseTokens()
  const syncMutation = useSyncHpxPulse()
  const updateMutation = useUpdateHpxPulse()
  const [wizardOpen, setWizardOpen] = useState(false)
  const [editingPulse, setEditingPulse] = useState<HpxPulseResponse | null>(null)
  const [joinCommands, setJoinCommands] = useState<JoinCommandSet | null>(null)
  const [syncingId, setSyncingId] = useState<number | null>(null)

  useEffect(() => {
    const handler = () => {
      setEditingPulse(null)
      setWizardOpen(true)
    }
    window.addEventListener('openHpxPulseDialog', handler)
    return () => window.removeEventListener('openHpxPulseDialog', handler)
  }, [])

  const copy = async (text: string) => {
    await navigator.clipboard.writeText(text)
    toast.success(t('copied', { defaultValue: 'Copied' }))
  }

  const runningCount = data?.pulses?.filter(p => p.status === 'running').length ?? 0

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium">
            {t('hpxPulse.summary', {
              defaultValue: '{{total}} pulse tunnel(s)',
              total: data?.total ?? 0,
            })}
          </p>
          {(data?.total ?? 0) > 0 && (
            <p className="text-muted-foreground mt-0.5 text-xs">
              {t('hpxPulse.runningCount', {
                defaultValue: '{{count}} running',
                count: runningCount,
              })}
            </p>
          )}
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" className="h-8 w-8 p-0" onClick={() => refetch()} disabled={isFetching}>
            <RefreshCw className={`size-3.5 ${isFetching ? 'animate-spin' : ''}`} />
          </Button>
          {canCreate && (
            <Button
              size="sm"
              className="h-8 gap-1.5"
              onClick={() => {
                setEditingPulse(null)
                setWizardOpen(true)
              }}
            >
              <Plus className="size-3.5" />
              {t('hpxPulse.add', { defaultValue: 'New Pulse' })}
            </Button>
          )}
        </div>
      </div>

      {isError && (
        <Card className="border-destructive/40 bg-destructive/5 space-y-1 p-4 text-sm">
          <p className="text-destructive font-medium">
            {t('hpxPulse.loadError', { defaultValue: 'Could not load Pulse tunnels from panel API' })}
          </p>
          <p className="text-muted-foreground text-xs">
            {t('hpxPulse.loadErrorHint', {
              defaultValue: 'Update panel, run DB migration (alembic upgrade head), and check hpx_pulse permissions.',
            })}
          </p>
          {(error as Error)?.message && (
            <p className="text-muted-foreground font-mono text-[11px]">{(error as Error).message}</p>
          )}
        </Card>
      )}

      {joinCommands && (
        <Card className="space-y-3 border-sky-500/20 bg-gradient-to-br from-sky-500/5 to-transparent p-4 text-xs">
          <div>
            <p className="text-sm font-semibold">{t('hpxPulse.installCommands', { defaultValue: 'Install commands' })}</p>
            <p className="text-muted-foreground mt-1 text-[11px] leading-relaxed">
              {t('hpxPulse.panelUrlWarning', {
                defaultValue:
                  'Use the exact panel URL below on both servers — a typo means agents join a different panel than this UI.',
              })}
            </p>
          </div>
          {joinCommands.iran && (
            <JoinCommandBlock label="Iran" primary={joinCommands.iran} alt={joinCommands.iranAlt} onCopy={copy} t={t} />
          )}
          {joinCommands.abroad && (
            <JoinCommandBlock
              label="Abroad"
              primary={joinCommands.abroad}
              primaryHint={t('hpxPulse.joinCommandPrimaryPanel', { defaultValue: 'Recommended (panel URL)' })}
              onCopy={copy}
              t={t}
            />
          )}
        </Card>
      )}

      {isLoading ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <Skeleton className="h-52 w-full rounded-xl" />
          <Skeleton className="h-52 w-full rounded-xl" />
        </div>
      ) : isError ? null : (data?.pulses?.length ?? 0) === 0 ? (
        <Card className="flex flex-col items-center justify-center gap-3 border-dashed p-12 text-center">
          <div className="bg-primary/10 text-primary flex size-12 items-center justify-center rounded-2xl">
            <Zap className="size-6" />
          </div>
          <div className="space-y-1">
            <p className="font-medium">{t('hpxPulse.emptyTitle', { defaultValue: 'No Pulse tunnels yet' })}</p>
            <p className="text-muted-foreground max-w-sm text-sm">
              {t('hpxPulse.empty', { defaultValue: 'Create one with the advisor wizard to deploy Iran + abroad agents.' })}
            </p>
          </div>
          {canCreate && (
            <Button
              size="sm"
              className="mt-1 gap-1.5"
              onClick={() => {
                setEditingPulse(null)
                setWizardOpen(true)
              }}
            >
              <Plus className="size-3.5" />
              {t('hpxPulse.add', { defaultValue: 'New Pulse' })}
            </Button>
          )}
        </Card>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {data!.pulses.map(pulse => (
            <PulseCard
              key={pulse.id}
              pulse={pulse}
              canUpdate={canUpdate}
              canDelete={canDelete}
              syncLoading={syncingId === pulse.id}
              onEdit={() => {
                setEditingPulse(pulse)
                setWizardOpen(true)
              }}
              onSync={async () => {
                setSyncingId(pulse.id)
                try {
                  const res = await syncMutation.mutateAsync(pulse.id)
                  toast.success(res.message ?? t('hpxPulse.syncSuccess', { defaultValue: 'Sync queued' }))
                } catch (e) {
                  toast.error((e as Error)?.message ?? t('error', { defaultValue: 'Error' }))
                } finally {
                  setSyncingId(null)
                }
              }}
              onAutoSync={async minutes => {
                try {
                  await updateMutation.mutateAsync({
                    id: pulse.id,
                    data: { auto_restart_interval_minutes: minutes },
                  })
                  toast.success(
                    minutes > 0
                      ? t('hpxPulse.autoSyncSaved', {
                          defaultValue: 'Auto sync enabled every {{minutes}} minutes',
                          minutes,
                        })
                      : t('hpxPulse.autoSyncDisabledSuccess', { defaultValue: 'Auto sync disabled' }),
                  )
                } catch (e) {
                  toast.error((e as Error)?.message ?? t('error', { defaultValue: 'Error' }))
                  throw e
                }
              }}
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
                setJoinCommands({
                  iran: res.iran_join_command ?? undefined,
                  iranAlt: res.iran_join_command_alt ?? undefined,
                  abroad: res.abroad_join_command ?? undefined,
                  abroadAlt: res.abroad_join_command_alt ?? undefined,
                })
              }}
            />
          ))}
        </div>
      )}

      <HpxPulseWizard
        open={wizardOpen}
        onOpenChange={open => {
          setWizardOpen(open)
          if (!open) setEditingPulse(null)
        }}
        editingPulse={editingPulse}
        onCreated={res => {
          setJoinCommands({
            iran: res.iran_join_command ?? undefined,
            iranAlt: res.iran_join_command_alt ?? undefined,
            abroad: res.abroad_join_command ?? undefined,
            abroadAlt: res.abroad_join_command_alt ?? undefined,
          })
          refetch()
        }}
      />
    </div>
  )
}
