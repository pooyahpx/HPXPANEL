import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type {
  HpxPulsePathPingResult,
  HpxPulseResponse,
  PathPingProto,
  PathPingTarget,
} from '@/service/api/hpx-pulse'
import { Activity, ArrowRight, Gauge, Radio, RefreshCw } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

function fmtMs(v: number | null | undefined) {
  if (v == null || Number.isNaN(v)) return '—'
  return `${v.toFixed(1)} ms`
}

function PathViz({
  pulse,
  pathPing,
  running,
}: {
  pulse: HpxPulseResponse
  pathPing?: HpxPulsePathPingResult | null
  running: boolean
}) {
  const { t } = useTranslation()
  const queued = pathPing?.status === 'queued'
  const done = pathPing?.status === 'done'
  const loss = pathPing?.loss_pct
  const healthy = done && (loss == null || loss < 50) && (pathPing?.avg_ms != null)
  const degraded = done && !healthy

  return (
    <div
      className={cn(
        'relative overflow-hidden rounded-xl border px-3 py-3',
        healthy && 'border-emerald-500/30 bg-gradient-to-r from-emerald-500/8 via-transparent to-emerald-500/8',
        degraded && 'border-amber-500/30 bg-gradient-to-r from-amber-500/8 via-transparent to-amber-500/8',
        queued && 'border-sky-500/30 bg-gradient-to-r from-sky-500/8 via-transparent to-sky-500/8',
        !healthy && !degraded && !queued && 'border-border/70 bg-muted/20',
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0 flex-1 text-center">
          <p className="text-muted-foreground text-[10px] font-medium tracking-wide uppercase">
            {t('hpxPulse.abroadAgent', { defaultValue: 'Abroad' })}
          </p>
          <p className="truncate font-mono text-xs font-semibold" dir="ltr" title={pulse.abroad_public_ip}>
            {pulse.abroad_public_ip || '—'}
          </p>
        </div>

        <div className="flex min-w-0 flex-[1.4] flex-col items-center gap-1.5 px-1">
          <div className="relative flex w-full items-center">
            <span
              className={cn(
                'size-2 shrink-0 rounded-full',
                pulse.abroad_claimed ? 'bg-emerald-500' : 'bg-muted-foreground/40',
              )}
            />
            <div className="relative mx-1 h-px flex-1 overflow-hidden bg-border">
              <div
                className={cn(
                  'absolute inset-y-0 w-1/3 bg-gradient-to-r from-transparent via-emerald-400 to-transparent',
                  (running || queued || isRunningStatus(pulse)) && 'animate-[path-ping-slide_1.4s_linear_infinite]',
                  degraded && 'via-amber-400',
                  !running && !queued && !isRunningStatus(pulse) && 'opacity-40',
                )}
              />
            </div>
            <ArrowRight
              className={cn(
                'size-3.5 shrink-0',
                healthy && 'text-emerald-500',
                degraded && 'text-amber-500',
                queued && 'text-sky-500 animate-pulse',
                !healthy && !degraded && !queued && 'text-muted-foreground',
              )}
            />
            <div className="relative mx-1 h-px flex-1 overflow-hidden bg-border">
              <div
                className={cn(
                  'absolute inset-y-0 w-1/3 bg-gradient-to-r from-transparent via-emerald-400 to-transparent',
                  (running || queued || isRunningStatus(pulse)) && 'animate-[path-ping-slide_1.4s_linear_infinite]',
                  degraded && 'via-amber-400',
                  !running && !queued && !isRunningStatus(pulse) && 'opacity-40',
                )}
                style={{ animationDelay: '0.35s' }}
              />
            </div>
            <span
              className={cn(
                'size-2 shrink-0 rounded-full',
                pulse.iran_claimed ? 'bg-emerald-500' : 'bg-muted-foreground/40',
              )}
            />
          </div>
          <div className="flex flex-wrap items-center justify-center gap-1.5">
            {pathPing?.proto ? (
              <Badge variant="secondary" className="h-5 rounded-md px-1.5 text-[10px] uppercase">
                {String(pathPing.proto)}
              </Badge>
            ) : null}
            {pathPing?.avg_ms != null ? (
              <span className="font-mono text-[11px] font-semibold tabular-nums" dir="ltr">
                {fmtMs(pathPing.avg_ms)}
              </span>
            ) : queued ? (
              <span className="text-sky-600 dark:text-sky-400 text-[11px]">
                {t('hpxPulse.pathPingQueued', { defaultValue: 'Sampling…' })}
              </span>
            ) : (
              <span className="text-muted-foreground text-[11px]">
                {t('hpxPulse.pathPingIdle', { defaultValue: 'Path ping idle' })}
              </span>
            )}
            {pathPing?.loss_pct != null ? (
              <span
                className={cn(
                  'font-mono text-[10px] tabular-nums',
                  pathPing.loss_pct > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-muted-foreground',
                )}
                dir="ltr"
              >
                {pathPing.loss_pct.toFixed(0)}% loss
              </span>
            ) : null}
          </div>
        </div>

        <div className="min-w-0 flex-1 text-center">
          <p className="text-muted-foreground text-[10px] font-medium tracking-wide uppercase">
            {t('hpxPulse.iranAgent', { defaultValue: 'Iran' })}
          </p>
          <p className="truncate font-mono text-xs font-semibold" dir="ltr" title={pulse.iran_public_ip}>
            {pathPing?.to || pulse.iran_public_ip || '—'}
          </p>
        </div>
      </div>
    </div>
  )
}

function isRunningStatus(pulse: HpxPulseResponse) {
  return pulse.status === 'running'
}

function SampleBars({ pathPing }: { pathPing?: HpxPulsePathPingResult | null }) {
  const replies = pathPing?.replies ?? []
  if (!replies.length) return null
  const max = Math.max(...replies.map(r => r.time_ms ?? 0), 1)

  return (
    <div className="flex items-end gap-1" dir="ltr">
      {replies.map(r => {
        const ok = r.status === 'ok' && r.time_ms != null
        const h = ok ? Math.max(12, Math.round(((r.time_ms ?? 0) / max) * 36)) : 10
        return (
          <div key={r.seq} className="flex flex-1 flex-col items-center gap-0.5" title={`${r.seq}: ${r.detail || r.status}`}>
            <div
              className={cn(
                'w-full max-w-6 rounded-sm transition-all',
                ok && 'bg-emerald-500/80',
                r.status === 'timeout' && 'bg-amber-500/70',
                r.status === 'error' && 'bg-destructive/70',
                !ok && r.status !== 'timeout' && r.status !== 'error' && 'bg-muted-foreground/40',
              )}
              style={{ height: h }}
            />
            <span className="text-muted-foreground text-[9px] tabular-nums">
              {ok ? `${Math.round(r.time_ms!)}` : '×'}
            </span>
          </div>
        )
      })}
    </div>
  )
}

export default function PathPingPanel({
  pulse,
  disabled,
  loading,
  canRun = true,
  onRun,
}: {
  pulse: HpxPulseResponse
  disabled?: boolean
  loading?: boolean
  canRun?: boolean
  onRun: (opts: { proto: PathPingProto; count: number; target: PathPingTarget }) => Promise<void>
}) {
  const { t } = useTranslation()
  const [proto, setProto] = useState<PathPingProto>('tcp')
  const [target, setTarget] = useState<PathPingTarget>('control')
  const pathPing = pulse.path_ping
  const queued = pathPing?.status === 'queued'
  const busy = Boolean(loading || queued)

  return (
    <div className="space-y-3 border-t pt-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <Radio className="text-primary size-3.5" />
          <p className="text-sm font-semibold">
            {t('hpxPulse.pathPing', { defaultValue: 'Path ping' })}
          </p>
          <Badge variant="outline" className="h-5 text-[10px]">
            {t('hpxPulse.pathPingAbroadToIran', { defaultValue: 'Abroad → Iran' })}
          </Badge>
        </div>
        {canRun ? (
          <div className="flex flex-wrap gap-1">
            {(['tcp', 'udp'] as const).map(p => (
              <Button
                key={p}
                type="button"
                size="sm"
                variant={proto === p ? 'default' : 'outline'}
                className="h-7 px-2.5 text-[11px] uppercase"
                disabled={busy}
                onClick={() => setProto(p)}
              >
                {p}
              </Button>
            ))}
            {(['control', 'forward'] as const).map(tg => (
              <Button
                key={tg}
                type="button"
                size="sm"
                variant={target === tg ? 'secondary' : 'outline'}
                className="h-7 px-2.5 text-[11px]"
                disabled={busy}
                onClick={() => setTarget(tg)}
              >
                {tg === 'control'
                  ? t('hpxPulse.pathPingControl', { defaultValue: 'Control' })
                  : t('hpxPulse.pathPingForward', { defaultValue: 'Forward' })}
              </Button>
            ))}
            <Button
              type="button"
              size="sm"
              className="h-7 gap-1.5 px-2.5 text-[11px]"
              disabled={disabled || busy || (!pulse.abroad_claimed && !pulse.iran_claimed)}
              onClick={() => void onRun({ proto, count: 4, target })}
            >
              {busy ? <RefreshCw className="size-3 animate-spin" /> : <Activity className="size-3" />}
              {t('hpxPulse.pathPingRun', { defaultValue: 'Run' })}
            </Button>
          </div>
        ) : null}
      </div>

      <PathViz pulse={pulse} pathPing={pathPing} running={busy} />

      {(pathPing?.status === 'done' || pathPing?.status === 'error' || (pathPing?.replies?.length ?? 0) > 0) && (
        <div className="grid gap-3 sm:grid-cols-[1fr_auto]">
          <SampleBars pathPing={pathPing} />
          <div className="grid grid-cols-3 gap-2 sm:min-w-44">
            <div className="rounded-lg border px-2 py-1.5">
              <p className="text-muted-foreground flex items-center gap-1 text-[9px] uppercase tracking-wide">
                <Gauge className="size-2.5" /> avg
              </p>
              <p className="font-mono text-xs font-semibold tabular-nums" dir="ltr">
                {fmtMs(pathPing?.avg_ms)}
              </p>
            </div>
            <div className="rounded-lg border px-2 py-1.5">
              <p className="text-muted-foreground text-[9px] uppercase tracking-wide">min / max</p>
              <p className="font-mono text-xs font-semibold tabular-nums" dir="ltr">
                {pathPing?.min_ms != null || pathPing?.max_ms != null
                  ? `${pathPing?.min_ms?.toFixed(0) ?? '—'} / ${pathPing?.max_ms?.toFixed(0) ?? '—'}`
                  : '—'}
              </p>
            </div>
            <div className="rounded-lg border px-2 py-1.5">
              <p className="text-muted-foreground text-[9px] uppercase tracking-wide">loss</p>
              <p className="font-mono text-xs font-semibold tabular-nums" dir="ltr">
                {pathPing?.loss_pct != null ? `${pathPing.loss_pct.toFixed(0)}%` : '—'}
              </p>
            </div>
          </div>
        </div>
      )}

      {pathPing?.port != null ? (
        <p className="text-muted-foreground text-[11px]" dir="ltr">
          {t('hpxPulse.pathPingTargetPort', {
            defaultValue: 'Target {{ip}}:{{port}} ({{target}})',
            ip: pathPing.to || pulse.iran_public_ip,
            port: pathPing.port,
            target: pathPing.target || target,
          })}
        </p>
      ) : null}
    </div>
  )
}
