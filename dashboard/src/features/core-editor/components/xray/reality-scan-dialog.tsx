import { FormEvent, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ChevronDown, CircleCheck, CircleHelp, CircleX, Loader2, Radar, ScanSearch, X } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { CoreEditorFormDialog } from '@/features/core-editor/components/shared/core-editor-form-dialog'
import { RealityScanResult, scanRealityTarget } from '@/service/reality-scan'
import dayjs from '@/lib/dayjs'
import { dateUtils } from '@/utils/dateFormatter'
import { cn } from '@/lib/utils'

interface RealityScanDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  initialTarget?: string
}

const MAX_TARGETS = 25
const SCAN_CONCURRENCY = 5

type RowStatus = 'pending' | 'scanning' | 'done' | 'error'

interface ScanRow {
  target: string
  status: RowStatus
  result?: RealityScanResult
  error?: string
}

function splitTokens(raw: string): string[] {
  return raw
    .split(/[\s,]+/)
    .map(part => part.trim())
    .filter(Boolean)
}

async function runPool<T>(items: T[], limit: number, worker: (item: T) => Promise<void>) {
  let cursor = 0
  const workers = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (cursor < items.length) {
      const item = items[cursor++]
      await worker(item)
    }
  })
  await Promise.all(workers)
}

const getErrorMessage = (error: unknown, fallback: string) => {
  if (!error || typeof error !== 'object') return fallback
  const maybeError = error as { data?: { detail?: unknown }; message?: string }
  const detail = maybeError.data?.detail
  if (typeof detail === 'string' && detail) return detail
  if (Array.isArray(detail)) {
    const joined = detail
      .map(item => (item && typeof item === 'object' && 'msg' in item ? String((item as { msg?: unknown }).msg ?? '') : String(item)))
      .filter(Boolean)
      .join('; ')
    if (joined) return joined
  }
  return maybeError.message || fallback
}

type TriState = boolean | null | undefined

function ProbeBadge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className={cn('reality-probe__badge', ok ? 'reality-probe__badge--ok' : 'reality-probe__badge--bad')} dir="ltr">
      {label}
    </span>
  )
}

function LatencyChip({ ms }: { ms: number | null | undefined }) {
  if (ms === null || ms === undefined) return null
  return (
    <span className="reality-probe__latency" dir="ltr">
      {ms} MS
    </span>
  )
}

function CheckRow({ status, label, detail }: { status: TriState; label: string; detail?: string }) {
  const icon =
    status === true ? (
      <CircleCheck className="h-4 w-4 shrink-0 text-[hsl(var(--neon-green))]" />
    ) : status === false ? (
      <CircleX className="text-destructive h-4 w-4 shrink-0" />
    ) : (
      <CircleHelp className="text-muted-foreground h-4 w-4 shrink-0" />
    )
  return (
    <div className="reality-probe__check">
      <div className="flex min-w-0 items-center gap-2.5">
        {icon}
        <span className="min-w-0 truncate text-sm font-medium">{label}</span>
      </div>
      {detail ? (
        <span className="text-muted-foreground shrink-0 font-mono text-[11px] tracking-wide" dir="ltr">
          {detail}
        </span>
      ) : null}
    </div>
  )
}

function RowStatusIcon({ row }: { row: ScanRow }) {
  if (row.status === 'scanning') return <Loader2 className="h-4 w-4 shrink-0 animate-spin text-sky-400" />
  if (row.status === 'pending') return <CircleHelp className="text-muted-foreground/35 h-4 w-4 shrink-0" />
  if (row.status === 'error') return <CircleX className="text-destructive h-4 w-4 shrink-0" />
  return row.result?.feasible ? <CircleCheck className="h-4 w-4 shrink-0 text-[hsl(var(--neon-green))]" /> : <CircleX className="text-destructive h-4 w-4 shrink-0" />
}

function ScanResultDetail({ result }: { result: RealityScanResult }) {
  const { t } = useTranslation()
  const keyExchangeDetail =
    result.curve ??
    (result.x25519 === null ? t('coreEditor.realityScan.unknown', { defaultValue: 'Unknown' }) : result.x25519 ? 'X25519' : t('coreEditor.realityScan.other', { defaultValue: 'Other' }))

  const formatExpiry = (iso: string | null) => {
    if (!iso) return null
    const d = dayjs(iso)
    if (!d.isValid()) return iso
    return `${d.fromNow()} (${dateUtils.formatDate(d.unix())})`
  }

  return (
    <div className="reality-probe__detail animate-rise space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          {result.feasible ? <CircleCheck className="h-5 w-5 shrink-0 text-[hsl(var(--neon-green))]" /> : <CircleX className="text-destructive h-5 w-5 shrink-0" />}
          <span className="font-mono text-sm font-semibold tracking-tight" dir="ltr">
            {result.host || result.target}
          </span>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <ProbeBadge ok={result.tls13} label="TLS 1.3" />
          <ProbeBadge ok={result.h2} label="H2" />
          <LatencyChip ms={result.latency_ms} />
        </div>
      </div>

      <div className={cn('reality-probe__banner', result.feasible ? 'reality-probe__banner--ok' : 'reality-probe__banner--bad')}>
        <div className="flex min-w-0 items-center gap-2">
          {result.feasible ? <CircleCheck className="h-4 w-4 shrink-0" /> : <CircleX className="h-4 w-4 shrink-0" />}
          <span className="text-sm font-semibold tracking-tight">
            {result.feasible
              ? t('coreEditor.realityScan.feasible', { defaultValue: 'Suitable Reality target' })
              : t('coreEditor.realityScan.notFeasible', { defaultValue: 'Not a suitable Reality target' })}
          </span>
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          <span className="font-mono text-[11px] tracking-wide opacity-90" dir="ltr">
            {result.host}
            {result.ip ? ` (${result.ip})` : ''}:{result.port}
          </span>
          <LatencyChip ms={result.latency_ms} />
        </div>
      </div>

      {result.sni ? (
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="font-hud text-muted-foreground text-[10px] tracking-[0.18em] uppercase">
            {t('coreEditor.realityScan.sniLabel', { defaultValue: 'SNI' })}
          </span>
          <span className="text-foreground font-mono break-all" dir="ltr">
            {result.sni}
          </span>
          {result.sni_discovered ? (
            <span className="reality-probe__chip reality-probe__chip--ghost">
              {t('coreEditor.realityScan.sniDiscovered', { defaultValue: 'discovered from IP' })}
            </span>
          ) : null}
        </div>
      ) : null}

      {result.reason ? (
        <Alert className="border-amber-500/30 bg-amber-500/5">
          <AlertDescription dir="ltr" className="font-mono text-xs text-amber-200/90">
            {result.reason}
          </AlertDescription>
        </Alert>
      ) : null}

      <div className="reality-probe__checks">
        <CheckRow status={result.tls13} label={t('coreEditor.realityScan.tls13', { defaultValue: 'TLS 1.3' })} detail={result.tls_version ? `TLS ${result.tls_version}` : undefined} />
        <CheckRow status={result.h2} label={t('coreEditor.realityScan.h2', { defaultValue: 'HTTP/2 (ALPN)' })} detail={result.alpn ?? undefined} />
        <CheckRow status={result.x25519} label={t('coreEditor.realityScan.keyExchange', { defaultValue: 'X25519 key exchange' })} detail={keyExchangeDetail ?? undefined} />
        <CheckRow
          status={result.post_quantum}
          label={t('coreEditor.realityScan.postQuantum', { defaultValue: 'Post-quantum (X25519MLKEM768)' })}
          detail={
            result.post_quantum === null
              ? t('coreEditor.realityScan.unknown', { defaultValue: 'Unknown' })
              : result.post_quantum
                ? t('coreEditor.realityScan.supported', { defaultValue: 'Supported' })
                : t('coreEditor.realityScan.notAdvertised', { defaultValue: 'Not offered' })
          }
        />
        <CheckRow
          status={result.h3}
          label={t('coreEditor.realityScan.h3', { defaultValue: 'HTTP/3 (advertised)' })}
          detail={result.h3 ? t('coreEditor.realityScan.advertised', { defaultValue: 'Alt-Svc' }) : t('coreEditor.realityScan.notAdvertised', { defaultValue: 'Not advertised' })}
        />
        <CheckRow status={result.cert_valid} label={t('coreEditor.realityScan.certificate', { defaultValue: 'Valid certificate' })} detail={result.cert_issuer ?? undefined} />
      </div>

      <div className="text-muted-foreground grid gap-2 text-xs sm:grid-cols-2">
        {result.cert_subject ? (
          <div className="min-w-0">
            <span className="font-hud tracking-[0.12em] uppercase opacity-70">{t('coreEditor.realityScan.subject', { defaultValue: 'Subject' })} · </span>
            <span className="text-foreground font-mono break-all" dir="ltr">
              {result.cert_subject}
            </span>
          </div>
        ) : null}
        {result.not_after ? (
          <div className="min-w-0">
            <span className="font-hud tracking-[0.12em] uppercase opacity-70">{t('coreEditor.realityScan.expires', { defaultValue: 'Expires' })} · </span>
            <span className="text-foreground font-mono" dir="ltr">
              {formatExpiry(result.not_after)}
            </span>
          </div>
        ) : null}
      </div>

      {result.server_names.length ? (
        <div className="space-y-2.5">
          <div className="font-hud text-muted-foreground text-[10px] font-semibold tracking-[0.16em] uppercase">
            {t('coreEditor.realityScan.serverNames', { defaultValue: 'Certificate server names (valid SNIs)' })}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {result.server_names.map(name => (
              <span key={name} className="reality-probe__chip" dir="ltr">
                {name}
              </span>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}

function ScanRowItem({ row, expanded, onToggle }: { row: ScanRow; expanded: boolean; onToggle: () => void }) {
  const { t } = useTranslation()
  const canExpand = row.status === 'done' || row.status === 'error'
  return (
    <div className={cn('reality-probe__row', expanded && 'reality-probe__row--open', row.status === 'done' && row.result?.feasible && 'reality-probe__row--ok')}>
      <button type="button" onClick={canExpand ? onToggle : undefined} className={cn('reality-probe__row-head', canExpand ? 'cursor-pointer' : 'cursor-default')}>
        <RowStatusIcon row={row} />
        <span className="min-w-0 flex-1 truncate font-mono text-sm tracking-tight" dir="ltr">
          {row.target}
        </span>
        {row.status === 'done' && row.result ? (
          <span className="hidden shrink-0 items-center gap-1.5 sm:flex">
            <ProbeBadge ok={row.result.tls13} label="TLS 1.3" />
            <ProbeBadge ok={row.result.h2} label="H2" />
            <LatencyChip ms={row.result.latency_ms} />
          </span>
        ) : row.status === 'scanning' ? (
          <span className="font-hud shrink-0 text-[10px] tracking-[0.14em] text-sky-400 uppercase">
            {t('coreEditor.realityScan.scanningShort', { defaultValue: 'Scanning' })}
          </span>
        ) : row.status === 'error' ? (
          <span className="text-destructive font-hud shrink-0 text-[10px] tracking-[0.14em] uppercase">
            {t('coreEditor.realityScan.scanFailed', { defaultValue: 'Failed' })}
          </span>
        ) : null}
        {canExpand ? <ChevronDown className={cn('text-muted-foreground h-4 w-4 shrink-0 transition-transform duration-200', expanded && 'rotate-180')} /> : <span className="w-4 shrink-0" />}
      </button>
      {expanded && row.status === 'done' && row.result ? (
        <div className="reality-probe__row-body">
          <ScanResultDetail result={row.result} />
        </div>
      ) : expanded && row.status === 'error' ? (
        <div className="reality-probe__row-body">
          <Alert variant="destructive">
            <AlertDescription dir="ltr" className="font-mono text-xs">
              {row.error}
            </AlertDescription>
          </Alert>
        </div>
      ) : null}
    </div>
  )
}

function TargetsInput({ value, onChange, disabled, max }: { value: string[]; onChange: (next: string[]) => void; disabled?: boolean; max: number }) {
  const { t } = useTranslation()
  const [draft, setDraft] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const addTokens = (raw: string) => {
    const next = [...value]
    for (const part of splitTokens(raw)) {
      if (next.length >= max) break
      if (!next.includes(part)) next.push(part)
    }
    if (next.length !== value.length) onChange(next)
  }

  const commitDraft = () => {
    if (!draft.trim()) return
    addTokens(draft)
    setDraft('')
  }

  return (
    <div
      className={cn('reality-probe__targets', disabled && 'pointer-events-none opacity-50')}
      dir="ltr"
      onMouseDown={event => {
        if (event.target === event.currentTarget) inputRef.current?.focus()
      }}
    >
      {value.map(tag => (
        <span key={tag} className="reality-probe__tag">
          <span className="truncate font-mono text-[11px] tracking-wide uppercase">{tag}</span>
          <button
            type="button"
            disabled={disabled}
            className="hover:bg-foreground/10 inline-flex shrink-0 rounded p-0.5"
            onClick={() => onChange(value.filter(item => item !== tag))}
            aria-label={t('coreEditor.realityScan.removeTarget', { defaultValue: 'Remove {{tag}}', tag })}
          >
            <X className="h-3 w-3" />
          </button>
        </span>
      ))}
      <input
        ref={inputRef}
        className="placeholder:text-muted-foreground/50 min-w-[8rem] flex-1 bg-transparent font-mono text-sm outline-none"
        value={draft}
        disabled={disabled}
        dir="ltr"
        autoComplete="off"
        spellCheck={false}
        placeholder={value.length ? '' : 'yahoo.com, google.com, play.google.com'}
        onChange={event => {
          const raw = event.target.value
          if (/[\s,]/.test(raw)) {
            addTokens(raw)
            setDraft('')
          } else {
            setDraft(raw)
          }
        }}
        onKeyDown={event => {
          if (event.key === 'Enter') {
            event.preventDefault()
            commitDraft()
          } else if (event.key === 'Backspace' && draft === '' && value.length) {
            onChange(value.slice(0, -1))
          }
        }}
        onPaste={event => {
          const text = event.clipboardData.getData('text')
          if (/[\s,\n]/.test(text)) {
            event.preventDefault()
            addTokens(text)
          }
        }}
        onBlur={commitDraft}
      />
    </div>
  )
}

export function RealityScanDialog({ open, onOpenChange, initialTarget }: RealityScanDialogProps) {
  const { t } = useTranslation()
  const [targets, setTargets] = useState<string[]>([])
  const [timeoutInput, setTimeoutInput] = useState('10')
  const [rows, setRows] = useState<ScanRow[]>([])
  const [expanded, setExpanded] = useState<string | null>(null)
  const [feasibleOnly, setFeasibleOnly] = useState(false)
  const [isScanning, setIsScanning] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    if (!open) {
      abortRef.current?.abort()
      abortRef.current = null
      setIsScanning(false)
      return
    }
    abortRef.current?.abort()
    abortRef.current = null
    setTargets(initialTarget?.trim() ? [initialTarget.trim()] : [])
    setRows([])
    setExpanded(null)
    setFeasibleOnly(false)
    setIsScanning(false)
  }, [open, initialTarget])

  useEffect(() => () => abortRef.current?.abort(), [])

  const canScan = targets.length > 0 && !isScanning

  const runScan = async () => {
    const list = targets
    if (!list.length) return
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    const parsedTimeout = Number(timeoutInput)
    const timeout = Number.isFinite(parsedTimeout) && parsedTimeout > 0 ? parsedTimeout : undefined
    setExpanded(list.length === 1 ? list[0] : null)
    setFeasibleOnly(false)
    setRows(list.map(target => ({ target, status: 'pending' as RowStatus })))
    setIsScanning(true)

    const patch = (target: string, next: Partial<ScanRow>) => {
      if (controller.signal.aborted) return
      setRows(prev => prev.map(row => (row.target === target ? { ...row, ...next } : row)))
    }

    try {
      await runPool(list, SCAN_CONCURRENCY, async target => {
        if (controller.signal.aborted) return
        patch(target, { status: 'scanning' })
        try {
          const res = await scanRealityTarget({ target, timeout }, controller.signal)
          if (controller.signal.aborted) return
          patch(target, { status: 'done', result: res })
        } catch (error) {
          if (controller.signal.aborted) return
          patch(target, { status: 'error', error: getErrorMessage(error, t('coreEditor.realityScan.errorDescription', { defaultValue: 'Unable to scan this target.' })) })
        }
      })
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null
        setIsScanning(false)
      }
    }
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    runScan()
  }

  const single = rows.length === 1 ? rows[0] : null
  const feasibleCount = rows.filter(row => row.status === 'done' && row.result?.feasible).length
  const displayedRows = feasibleOnly ? rows.filter(row => row.status === 'done' && row.result?.feasible) : rows

  return (
    <CoreEditorFormDialog
      isDialogOpen={open}
      onOpenChange={onOpenChange}
      title={
        <span className="font-hud tracking-[0.14em] uppercase">
          {t('coreEditor.realityScan.title', { defaultValue: 'Scan Reality target' })}
        </span>
      }
      leadingIcon={<ScanSearch className="h-5 w-5 shrink-0 text-sky-400" />}
      size="lg"
      className="reality-probe"
      inlinePersistValidation={false}
      footerExtra={
        isScanning ? (
          <Button
            type="button"
            variant="outline"
            className="reality-probe__btn-ghost"
            onClick={() => {
              abortRef.current?.abort()
              abortRef.current = null
              setIsScanning(false)
            }}
          >
            <Loader2 className="h-4 w-4 animate-spin" />
            <span>{t('coreEditor.realityScan.stop', { defaultValue: 'Stop' })}</span>
          </Button>
        ) : (
          <Button type="submit" form="reality-scan-form" disabled={!canScan} className="reality-probe__btn-scan">
            <ScanSearch className="h-4 w-4" />
            <span>
              {t('coreEditor.realityScan.scan', { defaultValue: 'Scan' })}
              {targets.length > 0 ? ` (${targets.length})` : ''}
            </span>
          </Button>
        )
      }
    >
      <div className="space-y-5">
        <p className="text-muted-foreground text-sm leading-relaxed">
          {t('coreEditor.realityScan.description', {
            defaultValue: 'Probe one or more targets to check they work as REALITY decoys. REALITY needs HTTP/2 and TLS 1.3.',
          })}
        </p>

        <form id="reality-scan-form" onSubmit={handleSubmit} className="grid items-start gap-4 sm:grid-cols-[minmax(0,1fr)_132px]">
          <div className="flex min-w-0 flex-col gap-2">
            <Label className="font-hud text-[10px] tracking-[0.16em] uppercase">
              {t('coreEditor.realityScan.targets', { defaultValue: 'Targets' })}
            </Label>
            <TargetsInput value={targets} onChange={setTargets} disabled={isScanning} max={MAX_TARGETS} />
            {targets.length >= MAX_TARGETS ? (
              <p className="text-muted-foreground text-xs">{t('coreEditor.realityScan.maxTargets', { defaultValue: 'Up to {{max}} targets can be scanned.', max: MAX_TARGETS })}</p>
            ) : null}
          </div>
          <div className="flex min-w-0 flex-col gap-2">
            <Label className="font-hud text-[10px] tracking-[0.16em] uppercase">
              {t('coreEditor.realityScan.timeout', { defaultValue: 'Timeout (s)' })}
            </Label>
            <Input
              className="reality-probe__timeout h-10 font-mono"
              value={timeoutInput}
              onChange={event => setTimeoutInput(event.target.value)}
              inputMode="numeric"
              type="number"
              min={1}
              max={20}
              disabled={isScanning}
              dir="ltr"
            />
          </div>
        </form>

        <div>
          {!rows.length ? (
            <div className="reality-probe__empty">
              <div className="reality-probe__radar" aria-hidden>
                <Radar className="h-8 w-8 text-sky-400/80" />
              </div>
              <p className="font-hud text-muted-foreground max-w-xs text-center text-[11px] tracking-[0.14em] uppercase">
                {t('coreEditor.realityScan.empty', { defaultValue: 'Enter one or more targets and run the scan.' })}
              </p>
            </div>
          ) : single ? (
            single.status === 'done' && single.result ? (
              <ScanResultDetail result={single.result} />
            ) : single.status === 'error' ? (
              <Alert variant="destructive">
                <AlertDescription dir="ltr" className="font-mono text-xs">
                  {single.error}
                </AlertDescription>
              </Alert>
            ) : (
              <div className="reality-probe__empty">
                <div className="reality-probe__radar reality-probe__radar--live" aria-hidden>
                  <Radar className="h-8 w-8 animate-pulse text-sky-400" />
                </div>
                <div className="flex items-center gap-2 text-sm text-sky-300/90">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span className="font-hud text-[11px] tracking-[0.16em] uppercase">
                    {t('coreEditor.realityScan.loading', { defaultValue: 'Scanning target...' })}
                  </span>
                </div>
              </div>
            )
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between gap-2">
                <span className="font-hud text-muted-foreground flex items-center gap-2 text-[11px] tracking-[0.14em] uppercase">
                  <span className="text-foreground font-mono text-sm tracking-normal normal-case">
                    {t('coreEditor.realityScan.summary', { defaultValue: '{{feasible}} / {{total}} suitable', feasible: feasibleCount, total: rows.length })}
                  </span>
                  {isScanning ? <Loader2 className="h-3.5 w-3.5 animate-spin text-sky-400" /> : null}
                  {!isScanning && feasibleCount > 0 ? <span className="online-beacon" /> : null}
                </span>
                <Button
                  type="button"
                  size="sm"
                  variant={feasibleOnly ? 'default' : 'outline'}
                  className={cn('h-8 text-[11px] tracking-wide', feasibleOnly && 'reality-probe__btn-scan')}
                  onClick={() => setFeasibleOnly(value => !value)}
                  disabled={!feasibleCount}
                >
                  {t('coreEditor.realityScan.suitableOnly', { defaultValue: 'Suitable only' })}
                </Button>
              </div>
              <div className="space-y-2">
                {displayedRows.map(row => (
                  <ScanRowItem key={row.target} row={row} expanded={expanded === row.target} onToggle={() => setExpanded(prev => (prev === row.target ? null : row.target))} />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </CoreEditorFormDialog>
  )
}
