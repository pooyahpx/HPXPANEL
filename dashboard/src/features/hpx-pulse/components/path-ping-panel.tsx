import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type {
  HpxPulsePathPingResult,
  HpxPulseResponse,
  PathPingProto,
  PathPingTarget,
} from '@/service/api/hpx-pulse'
import { Activity, ArrowRight, ChevronUp, Gauge, Rocket, RefreshCw, TriangleAlert } from 'lucide-react'
import { useEffect, useRef, useState, type ReactNode } from 'react'
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
                {t('hpxPulse.speedTest.running', { defaultValue: 'Testing tunnel…' })}
              </span>
            ) : (
              <span className="text-muted-foreground text-[11px]">
                {t('hpxPulse.speedTest.idle', { defaultValue: 'Ready to test' })}
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
                {pathPing.loss_pct.toFixed(0)}% {t('hpxPulse.speedTest.lossShort', { defaultValue: 'loss' })}
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

export type SpeedQuality = 'excellent' | 'good' | 'fair' | 'poor'

const HIGH_LOSS_PCT = 25

/** Latency/path quality grade — NOT bandwidth. Excellent <80ms, Good <150, Fair <300, Poor ≥300 or high loss. */
export function speedQuality(pathPing?: HpxPulsePathPingResult | null): SpeedQuality | null {
  if (!pathPing || pathPing.status !== 'done') return null
  const loss = pathPing.loss_pct ?? 0
  const avg = pathPing.avg_ms
  if (avg == null) return loss > 0 ? 'poor' : null
  if (loss >= HIGH_LOSS_PCT || avg >= 300) return 'poor'
  if (avg < 80) return 'excellent'
  if (avg < 150) return 'good'
  return 'fair'
}

const qualityTone: Record<SpeedQuality, string> = {
  excellent: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
  good: 'border-sky-500/40 bg-sky-500/10 text-sky-700 dark:text-sky-400',
  fair: 'border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400',
  poor: 'border-red-500/40 bg-red-500/10 text-red-700 dark:text-red-400',
}

function StatTile({ label, value, icon }: { label: string; value: string; icon?: ReactNode }) {
  return (
    <div className="rounded-lg border bg-background/40 px-2.5 py-2">
      <p className="text-muted-foreground flex items-center gap-1 text-[10px] uppercase tracking-wide">
        {icon}
        {label}
      </p>
      <p className="mt-0.5 font-mono text-sm font-semibold tabular-nums" dir="ltr">
        {value}
      </p>
    </div>
  )
}

export default function PathPingPanel({
  pulse,
  disabled,
  loading,
  canRun = true,
  onRun,
  onClose,
  focusSignal,
}: {
  pulse: HpxPulseResponse
  disabled?: boolean
  loading?: boolean
  canRun?: boolean
  onRun: (opts: { proto: PathPingProto; count: number; target: PathPingTarget }) => Promise<void>
  /** Collapse the panel (list wrapper owns visibility). */
  onClose?: () => void
  /** Bump to scroll this panel into view and focus the Start button. */
  focusSignal?: number
}) {
  const { t } = useTranslation()
  const [proto, setProto] = useState<PathPingProto>('tcp')
  // Forward = user path. Control probes can reset reverse/stealth tunnels.
  const [target, setTarget] = useState<PathPingTarget>('forward')
  const rootRef = useRef<HTMLDivElement>(null)
  const runRef = useRef<HTMLButtonElement>(null)
  const pathPing = pulse.path_ping
  const queued = pathPing?.status === 'queued'
  const busy = Boolean(loading || queued)
  const done = pathPing?.status === 'done'
  const failed = pathPing?.status === 'error'
  const quality = speedQuality(pathPing)
  const hasResult = done || failed || (pathPing?.replies?.length ?? 0) > 0
  const noAgent = !pulse.abroad_claimed && !pulse.iran_claimed

  useEffect(() => {
    if (!focusSignal) return
    rootRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    const id = window.setTimeout(() => runRef.current?.focus({ preventScroll: true }), 250)
    return () => window.clearTimeout(id)
  }, [focusSignal])

  return (
    <div
      ref={rootRef}
      id={`pulse-speed-test-${pulse.id}`}
      className="bg-gradient-to-br from-primary/5 via-transparent to-transparent space-y-3 rounded-xl border p-3 sm:p-4"
    >
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0 space-y-0.5">
          <div className="flex flex-wrap items-center gap-1.5">
            <Rocket className="text-primary size-4" />
            <p className="text-sm font-semibold">{t('hpxPulse.speedTest.title', { defaultValue: 'Tunnel speed test' })}</p>
            <Badge variant="outline" className="h-5 text-[10px]">
              {t('hpxPulse.pathPingAbroadToIran', { defaultValue: 'Abroad → Iran' })}
            </Badge>
            {quality ? (
              <Badge variant="outline" className={cn('h-5 text-[10px] font-semibold', qualityTone[quality])}>
                {t(`hpxPulse.speedTest.quality.${quality}`, { defaultValue: quality })}
              </Badge>
            ) : null}
          </div>
          <p className="text-muted-foreground text-[11px] leading-relaxed">
            {t('hpxPulse.speedTest.subtitle', {
              defaultValue:
                'Measures latency on the Forward (user) path. Prefer Forward — Control probes can reset reverse/stealth tunnels. Not a bandwidth (Mbps) test.',
            })}
          </p>
        </div>
        {onClose ? (
          <Button
            type="button"
            size="icon"
            variant="ghost"
            className="size-7"
            title={t('hpxPulse.speedTest.collapse', { defaultValue: 'Collapse' })}
            onClick={onClose}
          >
            <ChevronUp className="size-4" />
          </Button>
        ) : null}
      </div>

      {canRun ? (
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1" role="group" aria-label={t('hpxPulse.speedTest.protocol', { defaultValue: 'Protocol' })}>
            {(['tcp', 'udp'] as const).map(p => (
              <Button
                key={p}
                type="button"
                size="sm"
                variant={proto === p ? 'default' : 'outline'}
                className="h-8 px-3 text-[11px] uppercase"
                disabled={busy}
                onClick={() => setProto(p)}
              >
                {p}
              </Button>
            ))}
          </div>
          <div className="flex items-center gap-1" role="group" aria-label={t('hpxPulse.speedTest.endpoint', { defaultValue: 'Endpoint' })}>
            {(['control', 'forward'] as const).map(tg => (
              <Button
                key={tg}
                type="button"
                size="sm"
                variant={target === tg ? 'secondary' : 'outline'}
                className="h-8 px-3 text-[11px]"
                disabled={busy}
                onClick={() => setTarget(tg)}
              >
                {tg === 'control'
                  ? t('hpxPulse.pathPingControl', { defaultValue: 'Control' })
                  : t('hpxPulse.pathPingForward', { defaultValue: 'Forward' })}
              </Button>
            ))}
          </div>
          <Button
            ref={runRef}
            type="button"
            size="sm"
            className="ms-auto h-8 gap-1.5 px-4 text-xs font-semibold"
            disabled={disabled || busy || noAgent}
            onClick={() => void onRun({ proto, count: 4, target })}
          >
            {busy ? <RefreshCw className="size-3.5 animate-spin" /> : <Activity className="size-3.5" />}
            {busy
              ? t('hpxPulse.speedTest.running', { defaultValue: 'Testing tunnel…' })
              : hasResult
                ? t('hpxPulse.speedTest.runAgain', { defaultValue: 'Run again' })
                : t('hpxPulse.speedTest.start', { defaultValue: 'Start speed test' })}
          </Button>
        </div>
      ) : null}

      {canRun && noAgent ? (
        <p className="text-amber-700 dark:text-amber-400 flex items-center gap-1.5 text-[11px]">
          <TriangleAlert className="size-3.5 shrink-0" />
          {t('hpxPulse.pathPingNoAgent', { defaultValue: 'No agent joined — Tokens → join abroad first' })}
        </p>
      ) : null}

      <PathViz pulse={pulse} pathPing={pathPing} running={busy} />

      {!hasResult && !busy ? (
        <div className="text-muted-foreground rounded-lg border border-dashed px-3 py-4 text-center text-xs">
          <p className="text-foreground/80 font-medium">
            {t('hpxPulse.speedTest.emptyTitle', { defaultValue: 'No speed test yet' })}
          </p>
          <p className="mt-0.5">
            {t('hpxPulse.speedTest.emptyHint', {
              defaultValue: 'Pick TCP or UDP and Control or Forward, then start. Results appear here in a few seconds.',
            })}
          </p>
        </div>
      ) : null}

      {busy && !hasResult ? (
        <div className="text-muted-foreground flex items-center justify-center gap-2 rounded-lg border border-dashed border-sky-500/30 px-3 py-4 text-xs">
          <RefreshCw className="size-3.5 animate-spin text-sky-500" />
          {t('hpxPulse.speedTest.runningHint', { defaultValue: 'Agent is sampling the path — this takes a few seconds…' })}
        </div>
      ) : null}

      {failed ? (
        <p className="text-destructive text-xs">
          {t('hpxPulse.speedTest.failed', { defaultValue: 'Speed test failed' })}
          {pathPing?.detail ? `: ${pathPing.detail}` : ''}
        </p>
      ) : null}

      {hasResult && !failed ? (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            <StatTile
              label={t('hpxPulse.speedTest.avg', { defaultValue: 'Avg latency' })}
              value={fmtMs(pathPing?.avg_ms)}
              icon={<Gauge className="size-2.5" />}
            />
            <StatTile label={t('hpxPulse.speedTest.min', { defaultValue: 'Min' })} value={fmtMs(pathPing?.min_ms)} />
            <StatTile label={t('hpxPulse.speedTest.max', { defaultValue: 'Max' })} value={fmtMs(pathPing?.max_ms)} />
            <StatTile
              label={t('hpxPulse.speedTest.loss', { defaultValue: 'Packet loss' })}
              value={pathPing?.loss_pct != null ? `${pathPing.loss_pct.toFixed(0)}%` : '—'}
            />
          </div>
          <SampleBars pathPing={pathPing} />
          {quality ? (
            <p className="text-muted-foreground text-[11px]">
              {t('hpxPulse.speedTest.legend', {
                defaultValue: 'Quality: Excellent <80 ms · Good <150 ms · Fair <300 ms · Poor ≥300 ms or ≥25% loss',
              })}
            </p>
          ) : null}
        </div>
      ) : null}

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