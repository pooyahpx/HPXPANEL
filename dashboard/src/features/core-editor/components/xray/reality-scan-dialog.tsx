import { FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Check, ChevronDown, CircleCheck, CircleHelp, CircleX, Loader2, Radar, ScanSearch, Sparkles, X } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { CoreEditorFormDialog } from '@/features/core-editor/components/shared/core-editor-form-dialog'
import {
  REALITY_PRESET_TARGETS,
  RealityIranPath,
  RealityScanResult,
  RealityScanUsePayload,
  buildRealityUsePayload,
  scanRealityTarget,
} from '@/service/reality-scan'
import dayjs from '@/lib/dayjs'
import { dateUtils } from '@/utils/dateFormatter'
import { cn } from '@/lib/utils'

interface RealityScanDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  initialTarget?: string
  onUse?: (payload: RealityScanUsePayload) => void
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

function CheckRow({ status, label, detail }: { status: TriState; label: string; detail?: string }) {
  const icon =
    status === true ? (
      <CircleCheck className="h-4 w-4 shrink-0 text-emerald-500" />
    ) : status === false ? (
      <CircleX className="text-destructive h-4 w-4 shrink-0" />
    ) : (
      <CircleHelp className="text-muted-foreground h-4 w-4 shrink-0" />
    )
  return (
    <div className="flex items-center justify-between gap-3 py-2">
      <div className="flex min-w-0 items-center gap-2">
        {icon}
        <span className="min-w-0 truncate text-sm">{label}</span>
      </div>
      {detail ? (
        <span className="text-muted-foreground shrink-0 font-mono text-xs" dir="ltr">
          {detail}
        </span>
      ) : null}
    </div>
  )
}

function MiniBadge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className={cn('rounded px-1.5 py-0.5 font-mono text-[10px] font-medium', ok ? 'bg-emerald-500/10 text-emerald-500' : 'bg-destructive/10 text-destructive')} dir="ltr">
      {label}
    </span>
  )
}

function gradeTone(grade: string) {
  switch (grade) {
    case 'excellent':
      return 'border-emerald-500/35 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
    case 'good':
      return 'border-sky-500/35 bg-sky-500/10 text-sky-600 dark:text-sky-400'
    case 'fair':
      return 'border-amber-500/35 bg-amber-500/10 text-amber-700 dark:text-amber-400'
    case 'poor':
      return 'border-destructive/35 bg-destructive/10 text-destructive'
    default:
      return 'border-border bg-muted/40 text-muted-foreground'
  }
}

function IranPathPanel({ path, onUse, canUse }: { path: RealityIranPath; onUse?: () => void; canUse?: boolean }) {
  const { t } = useTranslation()
  return (
    <div className={cn('space-y-3 rounded-xl border p-3', gradeTone(path.grade))}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Radar className="h-4 w-4 shrink-0" />
          <span className="text-sm font-semibold">
            {t('coreEditor.realityScan.iranPathTitle', { defaultValue: 'Iran / Pulse fit' })}
          </span>
          <Badge variant="outline" className="font-mono text-[10px]" dir="ltr">
            {path.score}/100 · {path.grade}
          </Badge>
        </div>
        {canUse && onUse ? (
          <Button type="button" size="sm" className="h-8 gap-1.5" onClick={onUse}>
            <Check className="h-3.5 w-3.5" />
            {t('coreEditor.realityScan.useTarget', { defaultValue: 'Use' })}
          </Button>
        ) : null}
      </div>

      {path.iran_affinity ? (
        <p className="text-xs leading-relaxed opacity-90">{path.affinity_reason || t('coreEditor.realityScan.iranAffinityYes', { defaultValue: 'Strong Iran brand / .ir blend' })}</p>
      ) : (
        <p className="text-xs leading-relaxed opacity-90">
          {t('coreEditor.realityScan.iranAffinityNo', { defaultValue: 'Global decoy — works, but Iran ISP blend is weaker than Digikala-class targets.' })}
        </p>
      )}

      {path.pulse_checks.length ? (
        <div className="space-y-1.5">
          <div className="text-[11px] font-medium tracking-wide uppercase opacity-80">
            {t('coreEditor.realityScan.pulseChecks', { defaultValue: 'Pulse Iran entry' })}
          </div>
          <div className="space-y-1">
            {path.pulse_checks.map(check => (
              <div key={`${check.pulse_id}-${check.port}`} className="bg-background/50 flex items-center justify-between gap-2 rounded-lg border px-2.5 py-1.5 text-xs" dir="ltr">
                <div className="flex min-w-0 items-center gap-2">
                  {check.reachable ? <CircleCheck className="h-3.5 w-3.5 shrink-0 text-emerald-500" /> : <CircleX className="text-destructive h-3.5 w-3.5 shrink-0" />}
                  <span className="truncate font-mono">
                    #{check.pulse_id} {check.iran_ip}:{check.port}
                  </span>
                </div>
                <span className="text-muted-foreground shrink-0 font-mono">
                  {check.reachable ? `${check.latency_ms ?? '?'} ms` : check.detail || 'down'}
                </span>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {path.notes.length ? (
        <ul className="space-y-1 text-[11px] leading-relaxed opacity-90">
          {path.notes.map(note => (
            <li key={note} className="flex gap-1.5">
              <span className="opacity-50">•</span>
              <span>{note}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}

function RowStatusIcon({ row }: { row: ScanRow }) {
  if (row.status === 'scanning') return <Loader2 className="text-muted-foreground h-4 w-4 shrink-0 animate-spin" />
  if (row.status === 'pending') return <CircleHelp className="text-muted-foreground/40 h-4 w-4 shrink-0" />
  if (row.status === 'error') return <CircleX className="text-destructive h-4 w-4 shrink-0" />
  return row.result?.feasible ? <CircleCheck className="h-4 w-4 shrink-0 text-emerald-500" /> : <CircleX className="text-destructive h-4 w-4 shrink-0" />
}

function ScanResultDetail({ result, onUse }: { result: RealityScanResult; onUse?: (payload: RealityScanUsePayload) => void }) {
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

  const handleUse = () => onUse?.(buildRealityUsePayload(result))

  return (
    <div className="space-y-4">
      <div
        className={cn(
          'flex flex-col gap-3 rounded-xl border p-3 sm:flex-row sm:items-center sm:justify-between',
          result.feasible ? 'border-emerald-500/30 bg-emerald-500/10' : 'border-destructive/30 bg-destructive/10',
        )}
      >
        <div className="flex min-w-0 items-center gap-2">
          {result.feasible ? <CircleCheck className="h-5 w-5 shrink-0 text-emerald-500" /> : <CircleX className="text-destructive h-5 w-5 shrink-0" />}
          <div className="min-w-0">
            <div className="text-sm font-semibold">
              {result.feasible
                ? t('coreEditor.realityScan.feasible', { defaultValue: 'Suitable Reality target' })
                : t('coreEditor.realityScan.notFeasible', { defaultValue: 'Not a suitable Reality target' })}
            </div>
            <div className="text-muted-foreground truncate font-mono text-xs" dir="ltr">
              {result.host}
              {result.ip ? ` (${result.ip})` : ''}:{result.port}
            </div>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {result.latency_ms !== null ? (
            <Badge dir="ltr" variant="outline" className="font-mono text-xs">
              {result.latency_ms} ms
            </Badge>
          ) : null}
          {onUse && result.feasible ? (
            <Button type="button" size="sm" className="h-8 gap-1.5" onClick={handleUse}>
              <Check className="h-3.5 w-3.5" />
              {t('coreEditor.realityScan.useTarget', { defaultValue: 'Use' })}
            </Button>
          ) : null}
        </div>
      </div>

      {result.iran_path ? <IranPathPanel path={result.iran_path} onUse={handleUse} canUse={Boolean(onUse && result.feasible)} /> : null}

      {result.sni ? (
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="text-muted-foreground">{t('coreEditor.realityScan.sniLabel', { defaultValue: 'SNI' })}:</span>
          <span className="text-foreground font-mono break-all" dir="ltr">
            {result.sni}
          </span>
          {result.sni_discovered ? (
            <Badge variant="outline" className="text-[10px]">
              {t('coreEditor.realityScan.sniDiscovered', { defaultValue: 'discovered from IP' })}
            </Badge>
          ) : null}
        </div>
      ) : null}

      {result.reason ? (
        <Alert>
          <AlertDescription dir="ltr" className="font-mono text-xs">
            {result.reason}
          </AlertDescription>
        </Alert>
      ) : null}

      <div className="divide-border overflow-hidden rounded-xl border px-3">
        <CheckRow status={result.tls13} label={t('coreEditor.realityScan.tls13', { defaultValue: 'TLS 1.3' })} detail={result.tls_version ? `TLS ${result.tls_version}` : undefined} />
        <Separator />
        <CheckRow status={result.h2} label={t('coreEditor.realityScan.h2', { defaultValue: 'HTTP/2 (ALPN)' })} detail={result.alpn ?? undefined} />
        <Separator />
        <CheckRow status={result.x25519} label={t('coreEditor.realityScan.keyExchange', { defaultValue: 'X25519 key exchange' })} detail={keyExchangeDetail ?? undefined} />
        <Separator />
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
        <Separator />
        <CheckRow
          status={result.h3}
          label={t('coreEditor.realityScan.h3', { defaultValue: 'HTTP/3 (advertised)' })}
          detail={result.h3 ? t('coreEditor.realityScan.advertised', { defaultValue: 'Alt-Svc' }) : t('coreEditor.realityScan.notAdvertised', { defaultValue: 'Not advertised' })}
        />
        <Separator />
        <CheckRow status={result.cert_valid} label={t('coreEditor.realityScan.certificate', { defaultValue: 'Valid certificate' })} detail={result.cert_issuer ?? undefined} />
      </div>

      <div className="text-muted-foreground grid gap-2 text-xs sm:grid-cols-2">
        {result.cert_subject ? (
          <div className="min-w-0">
            <span>{t('coreEditor.realityScan.subject', { defaultValue: 'Subject' })}: </span>
            <span className="text-foreground break-all" dir="ltr">
              {result.cert_subject}
            </span>
          </div>
        ) : null}
        {result.not_after ? (
          <div className="min-w-0">
            <span>{t('coreEditor.realityScan.expires', { defaultValue: 'Expires' })}: </span>
            <span className="text-foreground" dir="ltr">
              {formatExpiry(result.not_after)}
            </span>
          </div>
        ) : null}
      </div>

      {result.server_names.length ? (
        <div className="space-y-2">
          <div className="text-muted-foreground text-xs font-medium">{t('coreEditor.realityScan.serverNames', { defaultValue: 'Certificate server names (valid SNIs)' })}</div>
          <div className="flex flex-wrap gap-1.5">
            {result.server_names.map(name => (
              <Badge key={name} dir="ltr" variant="secondary" className="font-mono text-xs">
                {name}
              </Badge>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}

function ScanRowItem({
  row,
  expanded,
  onToggle,
  onUse,
}: {
  row: ScanRow
  expanded: boolean
  onToggle: () => void
  onUse?: (payload: RealityScanUsePayload) => void
}) {
  const { t } = useTranslation()
  const canExpand = row.status === 'done' || row.status === 'error'
  return (
    <div className="overflow-hidden rounded-xl border">
      <div className="flex items-stretch">
        <button type="button" onClick={canExpand ? onToggle : undefined} className={cn('flex min-w-0 flex-1 items-center gap-2 px-3 py-2.5 text-left', canExpand ? 'hover:bg-muted/50' : 'cursor-default')}>
          <RowStatusIcon row={row} />
          <span className="min-w-0 flex-1 truncate font-mono text-sm" dir="ltr">
            {row.target}
          </span>
          {row.status === 'done' && row.result ? (
            <span className="hidden shrink-0 items-center gap-1.5 sm:flex">
              <MiniBadge ok={row.result.tls13} label="TLS 1.3" />
              <MiniBadge ok={row.result.h2} label="H2" />
              {row.result.iran_path ? (
                <Badge dir="ltr" variant="outline" className={cn('font-mono text-[10px]', gradeTone(row.result.iran_path.grade))}>
                  IR {row.result.iran_path.score}
                </Badge>
              ) : null}
              {row.result.latency_ms !== null ? (
                <Badge dir="ltr" variant="outline" className="font-mono text-[10px]">
                  {row.result.latency_ms} ms
                </Badge>
              ) : null}
            </span>
          ) : row.status === 'scanning' ? (
            <span className="text-muted-foreground shrink-0 text-xs">{t('coreEditor.realityScan.scanningShort', { defaultValue: 'Scanning' })}</span>
          ) : row.status === 'error' ? (
            <span className="text-destructive shrink-0 text-xs">{t('coreEditor.realityScan.scanFailed', { defaultValue: 'Failed' })}</span>
          ) : null}
          {canExpand ? <ChevronDown className={cn('text-muted-foreground h-4 w-4 shrink-0 transition-transform', expanded && 'rotate-180')} /> : <span className="w-4 shrink-0" />}
        </button>
        {row.status === 'done' && row.result?.feasible && onUse ? (
          <div className="border-l p-1.5">
            <Button
              type="button"
              size="sm"
              variant="secondary"
              className="h-full min-h-8 gap-1 px-2.5 text-xs"
              onClick={() => onUse(buildRealityUsePayload(row.result!))}
            >
              <Check className="h-3.5 w-3.5" />
              {t('coreEditor.realityScan.useTarget', { defaultValue: 'Use' })}
            </Button>
          </div>
        ) : null}
      </div>
      {expanded && row.status === 'done' && row.result ? (
        <div className="border-t p-3">
          <ScanResultDetail result={row.result} onUse={onUse} />
        </div>
      ) : expanded && row.status === 'error' ? (
        <div className="border-t p-3">
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
      className={cn(
        'border-input focus-within:ring-ring/40 flex min-h-11 w-full flex-wrap items-center gap-1.5 rounded-xl border bg-transparent px-2.5 py-1.5 text-sm shadow-xs focus-within:ring-2',
        disabled && 'pointer-events-none opacity-50',
      )}
      dir="ltr"
      onMouseDown={event => {
        if (event.target === event.currentTarget) inputRef.current?.focus()
      }}
    >
      {value.map(tag => (
        <Badge key={tag} variant="secondary" className="max-w-full gap-1 rounded-lg py-0.5 pr-1 pl-2 font-mono text-[11px] font-normal">
          <span className="truncate">{tag}</span>
          <button
            type="button"
            disabled={disabled}
            className="hover:bg-muted-foreground/20 inline-flex shrink-0 rounded p-0.5"
            onClick={() => onChange(value.filter(item => item !== tag))}
            aria-label={t('coreEditor.realityScan.removeTarget', { defaultValue: 'Remove {{tag}}', tag })}
          >
            <X className="h-3 w-3" />
          </button>
        </Badge>
      ))}
      <input
        ref={inputRef}
        className="placeholder:text-muted-foreground min-w-[8rem] flex-1 bg-transparent outline-none"
        value={draft}
        disabled={disabled}
        dir="ltr"
        autoComplete="off"
        spellCheck={false}
        placeholder={value.length ? '' : 'digikala.com:443, www.apple.com'}
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

export function RealityScanDialog({ open, onOpenChange, initialTarget, onUse }: RealityScanDialogProps) {
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
  const iranPresets = useMemo(() => REALITY_PRESET_TARGETS.filter(p => p.region === 'iran'), [])
  const globalPresets = useMemo(() => REALITY_PRESET_TARGETS.filter(p => p.region === 'global'), [])

  const togglePreset = (host: string) => {
    if (isScanning) return
    setTargets(prev => (prev.includes(host) ? prev.filter(item => item !== host) : prev.length >= MAX_TARGETS ? prev : [...prev, host]))
  }

  const handleUse = (payload: RealityScanUsePayload) => {
    onUse?.(payload)
    onOpenChange(false)
  }

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
          const res = await scanRealityTarget({ target, timeout, check_iran_path: true }, controller.signal)
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
      title={t('coreEditor.realityScan.title', { defaultValue: 'Scan Reality target' })}
      leadingIcon={<ScanSearch className="h-5 w-5 shrink-0" />}
      size="lg"
      inlinePersistValidation={false}
      footerExtra={
        isScanning ? (
          <Button
            type="button"
            variant="outline"
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
          <Button type="submit" form="reality-scan-form" disabled={!canScan}>
            <ScanSearch className="h-4 w-4" />
            <span>
              {t('coreEditor.realityScan.scan', { defaultValue: 'Scan' })}
              {targets.length > 1 ? ` (${targets.length})` : ''}
            </span>
          </Button>
        )
      }
    >
      <div className="space-y-5">
        <p className="text-muted-foreground text-sm leading-relaxed">
          {t('coreEditor.realityScan.description', {
            defaultValue: 'Probe decoys for REALITY (TLS 1.3 + HTTP/2 + X25519), score Iran blend, and check Pulse Iran entry IPs.',
          })}
        </p>

        <div className="space-y-2.5">
          <div className="flex items-center gap-2">
            <Sparkles className="text-muted-foreground h-3.5 w-3.5" />
            <span className="text-muted-foreground text-xs font-medium tracking-wide uppercase">
              {t('coreEditor.realityScan.presets', { defaultValue: 'Suggested targets' })}
            </span>
          </div>
          <div className="space-y-2">
            <div className="flex flex-wrap gap-1.5">
              {iranPresets.map(preset => {
                const active = targets.includes(preset.host)
                return (
                  <button
                    key={preset.host}
                    type="button"
                    disabled={isScanning}
                    onClick={() => togglePreset(preset.host)}
                    className={cn(
                      'rounded-full border px-2.5 py-1 text-xs transition-colors',
                      active ? 'border-emerald-500/40 bg-emerald-500/15 text-emerald-700 dark:text-emerald-300' : 'border-border bg-muted/30 hover:bg-muted/60 text-foreground',
                    )}
                    dir="ltr"
                    title={preset.host}
                  >
                    {preset.label}
                    <span className="text-muted-foreground ml-1 text-[10px]">IR</span>
                  </button>
                )
              })}
            </div>
            <div className="flex flex-wrap gap-1.5">
              {globalPresets.map(preset => {
                const active = targets.includes(preset.host)
                return (
                  <button
                    key={preset.host}
                    type="button"
                    disabled={isScanning}
                    onClick={() => togglePreset(preset.host)}
                    className={cn(
                      'rounded-full border px-2.5 py-1 text-xs transition-colors',
                      active ? 'border-sky-500/40 bg-sky-500/15 text-sky-700 dark:text-sky-300' : 'border-border bg-muted/30 hover:bg-muted/60 text-foreground',
                    )}
                    dir="ltr"
                    title={preset.host}
                  >
                    {preset.label}
                  </button>
                )
              })}
            </div>
          </div>
        </div>

        <form id="reality-scan-form" onSubmit={handleSubmit} className="grid items-start gap-4 sm:grid-cols-[minmax(0,1fr)_120px]">
          <div className="flex min-w-0 flex-col gap-2">
            <Label>{t('coreEditor.realityScan.targets', { defaultValue: 'Targets' })}</Label>
            <TargetsInput value={targets} onChange={setTargets} disabled={isScanning} max={MAX_TARGETS} />
            {targets.length >= MAX_TARGETS ? (
              <p className="text-muted-foreground text-xs">{t('coreEditor.realityScan.maxTargets', { defaultValue: 'Up to {{max}} targets can be scanned.', max: MAX_TARGETS })}</p>
            ) : null}
          </div>
          <div className="flex min-w-0 flex-col gap-2">
            <Label>{t('coreEditor.realityScan.timeout', { defaultValue: 'Timeout (s)' })}</Label>
            <Input className="h-11 rounded-xl" value={timeoutInput} onChange={event => setTimeoutInput(event.target.value)} inputMode="numeric" type="number" min={1} max={20} disabled={isScanning} dir="ltr" />
          </div>
        </form>

        <div>
          {!rows.length ? (
            <div className="from-muted/20 to-muted/5 text-muted-foreground flex min-h-44 flex-col items-center justify-center gap-2 rounded-xl border border-dashed bg-gradient-to-b px-4 text-center text-sm">
              <ScanSearch className="h-6 w-6 opacity-40" />
              <p>{t('coreEditor.realityScan.empty', { defaultValue: 'Pick a suggested target or type one, then Scan.' })}</p>
              <p className="text-xs opacity-70">{t('coreEditor.realityScan.emptyHint', { defaultValue: 'After a green result, press Use to fill dest + serverNames.' })}</p>
            </div>
          ) : single ? (
            single.status === 'done' && single.result ? (
              <ScanResultDetail result={single.result} onUse={onUse ? handleUse : undefined} />
            ) : single.status === 'error' ? (
              <Alert variant="destructive">
                <AlertDescription dir="ltr" className="font-mono text-xs">
                  {single.error}
                </AlertDescription>
              </Alert>
            ) : (
              <div className="flex min-h-44 items-center justify-center rounded-xl border border-dashed">
                <div className="text-muted-foreground flex items-center gap-2 text-sm">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {t('coreEditor.realityScan.loading', { defaultValue: 'Scanning target...' })}
                </div>
              </div>
            )
          ) : (
            <div className="space-y-2">
              <div className="flex items-center justify-between gap-2">
                <span className="text-muted-foreground text-sm">
                  {t('coreEditor.realityScan.summary', { defaultValue: '{{feasible}} / {{total}} suitable', feasible: feasibleCount, total: rows.length })}
                  {isScanning ? <Loader2 className="ml-2 inline h-3.5 w-3.5 animate-spin align-[-2px]" /> : null}
                </span>
                <Button type="button" size="sm" variant={feasibleOnly ? 'default' : 'outline'} className="h-7 text-xs" onClick={() => setFeasibleOnly(value => !value)} disabled={!feasibleCount}>
                  {t('coreEditor.realityScan.suitableOnly', { defaultValue: 'Suitable only' })}
                </Button>
              </div>
              <div className="space-y-1.5">
                {displayedRows.map(row => (
                  <ScanRowItem
                    key={row.target}
                    row={row}
                    expanded={expanded === row.target}
                    onToggle={() => setExpanded(prev => (prev === row.target ? null : row.target))}
                    onUse={onUse ? handleUse : undefined}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </CoreEditorFormDialog>
  )
}
