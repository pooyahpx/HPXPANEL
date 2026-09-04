import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useAdmin } from '@/hooks/use-admin'
import useDirDetection from '@/hooks/use-dir-detection'
import { AuditLogQuery, downloadAuditCsv, useAuditLog, useAuditLogs } from '@/service/api/audit'
import { hasPermission } from '@/utils/rbac'
import { ChevronLeft, ChevronRight, Download, FileClock, RotateCcw, Search } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'

const PAGE_SIZE = 25
const toLocalDateTimeInput = (value?: string) => {
  if (!value) return ''
  const date = new Date(value)
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000).toISOString().slice(0, 16)
}

const JsonPanel = ({ title, value }: { title: string; value: unknown }) => (
  <section className="min-w-0">
    <h3 className="text-muted-foreground mb-2 font-mono text-[10px] font-bold tracking-[0.14em] uppercase">{title}</h3>
    <pre className="bg-muted/50 max-h-80 overflow-auto border p-3 text-start font-mono text-[11px] leading-relaxed whitespace-pre-wrap">{value == null ? '—' : JSON.stringify(value, null, 2)}</pre>
  </section>
)

const AuditPage = () => {
  const { t } = useTranslation()
  const dir = useDirDetection()
  const { admin } = useAdmin()
  const canView = hasPermission(admin, 'audit_logs', 'read')
  const [filters, setFilters] = useState<Omit<AuditLogQuery, 'offset' | 'limit'>>({})
  const [page, setPage] = useState(0)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const query = useMemo<AuditLogQuery>(() => ({ ...filters, offset: page * PAGE_SIZE, limit: PAGE_SIZE }), [filters, page])
  const { data, isLoading, isError } = useAuditLogs(query, canView)
  const { data: selected } = useAuditLog(selectedId, canView)
  const pages = Math.max(1, Math.ceil((data?.total ?? 0) / PAGE_SIZE))

  const updateFilter = (key: keyof typeof filters, value?: string) => {
    setFilters(current => ({ ...current, [key]: value || undefined }))
    setPage(0)
  }

  if (!canView) return <div className="p-6 text-sm">{t('audit.denied')}</div>

  return (
    <div dir={dir} className="w-full">
      <header className="mission-brief border-b">
        <div className="mx-auto flex w-full max-w-[1800px] flex-col gap-4 px-4 py-6 md:px-6 md:py-8 lg:flex-row lg:items-end lg:justify-between">
          <div className="border-primary border-s-2 ps-4">
            <div className="text-primary mb-2 flex items-center gap-2 font-mono text-[10px] font-bold tracking-[0.18em] uppercase">
              <FileClock className="h-3.5 w-3.5" /> HPXPANEL / {t('audit.title')}
            </div>
            <h1 className="font-display text-3xl leading-none font-black tracking-[-0.04em] uppercase sm:text-4xl">{t('audit.title')}</h1>
            <p className="text-muted-foreground mt-2 text-sm">{t('audit.subtitle')}</p>
          </div>
          <Button variant="outline" onClick={() => downloadAuditCsv(filters)}>
            <Download className="me-2 h-4 w-4" />
            {t('audit.export')}
          </Button>
        </div>
      </header>

      <main className="mx-auto w-full max-w-[1800px] space-y-4 px-3 py-4 sm:px-4 md:px-6 md:py-6">
        <Card className="rounded-none">
          <CardContent className="grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
            <label className="relative sm:col-span-2">
              <span className="sr-only">{t('audit.search')}</span>
              <Search className="text-muted-foreground absolute start-3 top-3.5 h-4 w-4" />
              <Input className="ps-10" value={filters.search ?? ''} onChange={event => updateFilter('search', event.target.value)} placeholder={t('audit.search')} />
            </label>
            <Input value={filters.actor ?? ''} onChange={event => updateFilter('actor', event.target.value)} placeholder={t('audit.actor')} aria-label={t('audit.actor')} />
            <Input value={filters.action ?? ''} onChange={event => updateFilter('action', event.target.value)} placeholder={t('audit.action')} aria-label={t('audit.action')} />
            <Input value={filters.resource ?? ''} onChange={event => updateFilter('resource', event.target.value)} placeholder={t('audit.resource')} aria-label={t('audit.resource')} />
            <Select value={filters.result ?? 'all'} onValueChange={value => updateFilter('result', value === 'all' ? undefined : value)}>
              <SelectTrigger aria-label={t('audit.result')}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t('audit.allResults')}</SelectItem>
                <SelectItem value="success">{t('audit.success')}</SelectItem>
                <SelectItem value="failure">{t('audit.failure')}</SelectItem>
              </SelectContent>
            </Select>
            <Button
              variant="ghost"
              onClick={() => {
                setFilters({})
                setPage(0)
              }}
            >
              <RotateCcw className="me-2 h-4 w-4" />
              {t('audit.reset')}
            </Button>
            <label className="space-y-1 sm:col-span-2">
              <span className="text-muted-foreground font-mono text-[10px] uppercase">{t('audit.from')}</span>
              <Input
                type="datetime-local"
                value={toLocalDateTimeInput(filters.start)}
                onChange={event => updateFilter('start', event.target.value ? new Date(event.target.value).toISOString() : undefined)}
              />
            </label>
            <label className="space-y-1 sm:col-span-2">
              <span className="text-muted-foreground font-mono text-[10px] uppercase">{t('audit.to')}</span>
              <Input
                type="datetime-local"
                value={toLocalDateTimeInput(filters.end)}
                onChange={event => updateFilter('end', event.target.value ? new Date(event.target.value).toISOString() : undefined)}
              />
            </label>
          </CardContent>
        </Card>

        {isError && <p className="text-destructive text-sm">{t('audit.loadError')}</p>}
        <div className="hidden md:block">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t('audit.time')}</TableHead>
                <TableHead>{t('audit.actor')}</TableHead>
                <TableHead>{t('audit.action')}</TableHead>
                <TableHead>{t('audit.resource')}</TableHead>
                <TableHead>{t('audit.result')}</TableHead>
                <TableHead>{t('audit.sourceIp')}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data?.logs.map(log => (
                <TableRow key={log.id} className="cursor-pointer" tabIndex={0} onClick={() => setSelectedId(log.id)} onKeyDown={event => event.key === 'Enter' && setSelectedId(log.id)}>
                  <TableCell className="font-mono text-xs whitespace-nowrap">{new Date(log.created_at).toLocaleString()}</TableCell>
                  <TableCell>{log.actor_username ?? `#${log.actor_id ?? '—'}`}</TableCell>
                  <TableCell className="font-mono text-xs">{log.action}</TableCell>
                  <TableCell className="font-mono text-xs">
                    {log.resource}
                    {log.resource_id ? ` / ${log.resource_id}` : ''}
                  </TableCell>
                  <TableCell>
                    <Badge variant={log.result === 'success' ? 'secondary' : 'destructive'}>{t(`audit.${log.result}`)}</Badge>
                  </TableCell>
                  <TableCell className="font-mono text-xs">{log.source_ip ?? '—'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>

        <div className="grid gap-3 md:hidden">
          {data?.logs.map(log => (
            <button key={log.id} type="button" onClick={() => setSelectedId(log.id)} className="bg-card w-full border-2 p-4 text-start shadow-[3px_3px_0_0_hsl(var(--pixel-border))]">
              <div className="flex items-start justify-between gap-2">
                <span className="font-mono text-xs font-bold">
                  {log.resource} / {log.action}
                </span>
                <Badge variant={log.result === 'success' ? 'secondary' : 'destructive'}>{t(`audit.${log.result}`)}</Badge>
              </div>
              <p className="text-muted-foreground mt-2 text-xs">
                {log.actor_username ?? `#${log.actor_id ?? '—'}`} · {new Date(log.created_at).toLocaleString()}
              </p>
            </button>
          ))}
        </div>

        {!isLoading && data?.logs.length === 0 && <p className="text-muted-foreground py-10 text-center text-sm">{t('audit.empty')}</p>}
        <div className="flex items-center justify-between gap-3">
          <p className="text-muted-foreground font-mono text-xs">{t('audit.total', { count: data?.total ?? 0 })}</p>
          <div className="flex items-center gap-2">
            <Button size="icon" variant="outline" disabled={page === 0} onClick={() => setPage(value => value - 1)} aria-label={t('audit.previous')}>
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="min-w-20 text-center font-mono text-xs">
              {page + 1} / {pages}
            </span>
            <Button size="icon" variant="outline" disabled={page + 1 >= pages} onClick={() => setPage(value => value + 1)} aria-label={t('audit.next')}>
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </main>

      <Dialog open={selectedId !== null} onOpenChange={open => !open && setSelectedId(null)}>
        <DialogContent className="max-h-[90vh] max-w-5xl overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {t('audit.details')} #{selected?.id ?? selectedId}
            </DialogTitle>
            <DialogDescription>{selected ? `${selected.actor_username ?? selected.actor_id ?? '—'} · ${selected.resource} · ${selected.action}` : t('audit.loading')}</DialogDescription>
          </DialogHeader>
          {selected && (
            <div className="space-y-4">
              <div className="grid gap-2 text-xs sm:grid-cols-2 lg:grid-cols-4">
                <div>
                  <span className="text-muted-foreground">{t('audit.time')}:</span> {new Date(selected.created_at).toLocaleString()}
                </div>
                <div>
                  <span className="text-muted-foreground">{t('audit.sourceIp')}:</span> {selected.source_ip ?? '—'}
                </div>
                <div>
                  <span className="text-muted-foreground">{t('audit.resourceId')}:</span> {selected.resource_id ?? '—'}
                </div>
                <div>
                  <span className="text-muted-foreground">{t('audit.result')}:</span> {t(`audit.${selected.result}`)}
                </div>
              </div>
              {selected.detail && <p className="border-s-destructive border-s-2 ps-3 text-sm">{selected.detail}</p>}
              <div className="grid gap-4 lg:grid-cols-2">
                <JsonPanel title={t('audit.before')} value={selected.before} />
                <JsonPanel title={t('audit.after')} value={selected.after} />
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default AuditPage
