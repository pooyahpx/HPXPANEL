import type { SubscriptionFormData } from '@/features/subscriptions/components/subscription-settings-schema'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'
import { fetcher } from '@/service/http'
import { Activity, Gauge, Plus, Trash2, Link2, Zap } from 'lucide-react'
import { useState } from 'react'
import { UseFormReturn, useFieldArray, useWatch } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

export interface SubscriptionExternalConfigsSectionProps {
  form: UseFormReturn<SubscriptionFormData>
  /** Standalone category page uses a denser glass layout */
  standalone?: boolean
}

type ProbeResult = {
  ok: boolean
  host?: string | null
  port?: number | null
  protocol?: string | null
  ping?: {
    ok?: boolean
    avg_ms?: number | null
    min_ms?: number | null
    max_ms?: number | null
    loss_pct?: number | null
  } | null
  speed?: {
    ok?: boolean
    mbps?: number | null
    tcp_connect_ms?: number | null
    note?: string | null
    error?: string | null
  } | null
  error?: string | null
}

function ProbeMeter({
  label,
  value,
  hint,
  loading,
  accent,
}: {
  label: string
  value: string
  hint?: string
  loading?: boolean
  accent?: 'emerald' | 'sky' | 'amber'
}) {
  const ring =
    accent === 'sky'
      ? 'border-sky-500/30 from-sky-500/10'
      : accent === 'amber'
        ? 'border-amber-500/30 from-amber-500/10'
        : 'border-emerald-500/30 from-emerald-500/10'
  return (
    <div className={cn('rounded-xl border bg-gradient-to-br to-transparent px-3 py-2.5', ring)}>
      <p className="text-muted-foreground text-[10px] font-medium tracking-wide uppercase">{label}</p>
      <p className={cn('mt-1 font-mono text-sm font-semibold tabular-nums', loading && 'animate-pulse')}>{value}</p>
      {hint ? <p className="text-muted-foreground mt-0.5 text-[10px] leading-snug">{hint}</p> : null}
    </div>
  )
}

function ExternalConfigCard({
  form,
  index,
  onRemove,
  t,
}: {
  form: UseFormReturn<SubscriptionFormData>
  index: number
  onRemove: () => void
  t: (k: string, o?: Record<string, unknown>) => string
}) {
  const link = useWatch({ control: form.control, name: `external_configs.${index}.link` })
  const name = useWatch({ control: form.control, name: `external_configs.${index}.name` })
  const [probe, setProbe] = useState<ProbeResult | null>(null)
  const [pingLoading, setPingLoading] = useState(false)
  const [speedLoading, setSpeedLoading] = useState(false)

  const runProbe = async (mode: 'ping' | 'speed' | 'both') => {
    const trimmed = (link || '').trim()
    if (trimmed.length < 8) {
      toast.error(t('settings.motherConfigs.linkRequired', { defaultValue: 'Paste a share link first' }))
      return
    }
    if (mode === 'ping' || mode === 'both') setPingLoading(true)
    if (mode === 'speed' || mode === 'both') setSpeedLoading(true)
    try {
      const res = (await fetcher('/api/settings/subscription/external-configs/probe', {
        method: 'POST',
        body: { link: trimmed, mode, samples: 5 },
      })) as ProbeResult
      setProbe(prev => ({
        ...(prev || {}),
        ...res,
        ping: mode === 'speed' ? prev?.ping : res.ping,
        speed: mode === 'ping' ? prev?.speed : res.speed,
      }))
      if (!res.ok && res.error) {
        toast.error(res.error)
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Probe failed')
    } finally {
      setPingLoading(false)
      setSpeedLoading(false)
    }
  }

  return (
    <Card className="border-border/60 bg-card/40 space-y-4 overflow-hidden p-4 backdrop-blur-md sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline" className="border-emerald-500/35 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400">
              {t('settings.motherConfigs.badge', { defaultValue: 'Mother config' })}
            </Badge>
            {name ? (
              <span className="truncate text-sm font-semibold">{name}</span>
            ) : (
              <span className="text-muted-foreground text-sm">
                {t('settings.motherConfigs.unnamed', { defaultValue: 'Untitled config' })}
              </span>
            )}
          </div>
          <p className="text-muted-foreground text-[11px] leading-relaxed">
            {t('settings.motherConfigs.cardHint', {
              defaultValue: 'Shown in user subs only while that user still has remaining volume on this panel.',
            })}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <FormField
            control={form.control}
            name={`external_configs.${index}.enabled`}
            render={({ field }) => (
              <FormItem className="flex flex-row items-center gap-2 space-y-0">
                <FormControl>
                  <Switch checked={field.value} onCheckedChange={field.onChange} className="cursor-pointer" />
                </FormControl>
                <FormLabel className="text-xs font-medium">
                  {t('settings.motherConfigs.enabled', { defaultValue: 'On in subs' })}
                </FormLabel>
              </FormItem>
            )}
          />
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="text-destructive hover:text-destructive cursor-pointer"
            onClick={onRemove}
            aria-label={t('delete', { defaultValue: 'Delete' })}
          >
            <Trash2 className="size-4" />
          </Button>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <FormField
          control={form.control}
          name={`external_configs.${index}.name`}
          render={({ field }) => (
            <FormItem className="space-y-2">
              <FormLabel className="text-xs sm:text-sm">
                {t('settings.motherConfigs.name', { defaultValue: 'Display name' })}
              </FormLabel>
              <FormControl>
                <Input
                  placeholder={t('settings.motherConfigs.namePlaceholder', { defaultValue: 'Mother · Reality' })}
                  className="text-xs sm:text-sm"
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name={`external_configs.${index}.personalize`}
          render={({ field }) => (
            <FormItem className="bg-amber-500/5 flex flex-col gap-2 rounded-xl border border-amber-500/25 px-3 py-2.5">
              <div className="flex flex-row items-center justify-between gap-3">
                <div className="space-y-0.5">
                  <FormLabel className="text-xs font-medium sm:text-sm">
                    {t('settings.motherConfigs.personalize', { defaultValue: 'Bind local user UUID' })}
                  </FormLabel>
                  <FormDescription className="text-[11px] leading-snug">
                    {t('settings.motherConfigs.personalizeHint', {
                      defaultValue:
                        'Keep OFF for normal mother share links (shared UUID). Turn ON only if the mother server is a Node of this panel / has the same user clients — otherwise configs will not connect.',
                    })}
                  </FormDescription>
                </div>
                <FormControl>
                  <Switch checked={field.value === true} onCheckedChange={field.onChange} className="cursor-pointer" />
                </FormControl>
              </div>
              {field.value === true ? (
                <p className="text-[11px] leading-snug text-amber-700 dark:text-amber-300">
                  {t('settings.motherConfigs.personalizeWarn', {
                    defaultValue:
                      'Warning: UUID is rewritten per user. If mother is a foreign freeloader link, turn this OFF or users cannot connect (panel ping can still succeed).',
                  })}
                </p>
              ) : null}
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name={`external_configs.${index}.respect_user_quota`}
          render={({ field }) => (
            <FormItem className="bg-muted/20 flex flex-row items-center justify-between gap-3 rounded-xl border px-3 py-2.5">
              <div className="space-y-0.5">
                <FormLabel className="text-xs font-medium sm:text-sm">
                  {t('settings.motherConfigs.respectQuota', { defaultValue: 'Respect user volume' })}
                </FormLabel>
                <FormDescription className="text-[11px] leading-snug">
                  {t('settings.motherConfigs.respectQuotaHint', {
                    defaultValue:
                      'Off = every active user gets it (only when Bind UUID is on). Shared freeloader mode always respects volume.',
                  })}
                </FormDescription>
              </div>
              <FormControl>
                <Switch checked={field.value} onCheckedChange={field.onChange} className="cursor-pointer" />
              </FormControl>
            </FormItem>
          )}
        />
      </div>

      <FormField
        control={form.control}
        name={`external_configs.${index}.link`}
        render={({ field }) => (
          <FormItem className="space-y-2">
            <FormLabel className="text-xs sm:text-sm">
              {t('settings.motherConfigs.link', { defaultValue: 'Share link' })}
            </FormLabel>
            <FormControl>
              <Textarea
                rows={3}
                dir="ltr"
                placeholder="vless://uuid@host:port?encryption=none&security=reality&..."
                className="resize-y font-mono text-[11px] sm:text-xs"
                {...field}
              />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />

      <div className="grid gap-2 sm:grid-cols-2">
        <ProbeMeter
          label={t('settings.motherConfigs.livePing', { defaultValue: 'Live ping' })}
          loading={pingLoading}
          accent="emerald"
          value={
            pingLoading
              ? '…'
              : probe?.ping?.avg_ms != null
                ? `${probe.ping.avg_ms.toFixed(1)} ms`
                : '—'
          }
          hint={
            probe?.ping?.loss_pct != null
              ? t('settings.motherConfigs.pingHint', {
                  defaultValue: 'loss {{loss}}% · min {{min}} · max {{max}}',
                  loss: probe.ping.loss_pct,
                  min: probe.ping.min_ms ?? '—',
                  max: probe.ping.max_ms ?? '—',
                })
              : t('settings.motherConfigs.pingIdle', { defaultValue: 'TCP to node host:port' })
          }
        />
        <ProbeMeter
          label={t('settings.motherConfigs.speedTest', { defaultValue: 'Speed test' })}
          loading={speedLoading}
          accent="sky"
          value={
            speedLoading
              ? '…'
              : probe?.speed?.mbps != null
                ? `${probe.speed.mbps.toFixed(1)} Mbps`
                : probe?.speed?.tcp_connect_ms != null
                  ? `${probe.speed.tcp_connect_ms.toFixed(0)} ms TCP`
                  : '—'
          }
          hint={
            probe?.speed?.note ||
            t('settings.motherConfigs.speedIdle', { defaultValue: 'Front/path download from panel' })
          }
        />
      </div>

      <div className="flex flex-wrap gap-2">
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="h-8 cursor-pointer gap-1.5"
          disabled={pingLoading}
          onClick={() => runProbe('ping')}
        >
          <Activity className={cn('size-3.5', pingLoading && 'animate-pulse')} />
          {t('settings.motherConfigs.runPing', { defaultValue: 'Ping' })}
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          className="h-8 cursor-pointer gap-1.5"
          disabled={speedLoading}
          onClick={() => runProbe('speed')}
        >
          <Gauge className={cn('size-3.5', speedLoading && 'animate-pulse')} />
          {t('settings.motherConfigs.runSpeed', { defaultValue: 'Speed' })}
        </Button>
        <Button
          type="button"
          size="sm"
          variant="secondary"
          className="h-8 cursor-pointer gap-1.5"
          disabled={pingLoading || speedLoading}
          onClick={() => runProbe('both')}
        >
          <Zap className="size-3.5" />
          {t('settings.motherConfigs.runBoth', { defaultValue: 'Ping + Speed' })}
        </Button>
      </div>
    </Card>
  )
}

export function SubscriptionExternalConfigsSection({ form, standalone = false }: SubscriptionExternalConfigsSectionProps) {
  const { t } = useTranslation()
  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: 'external_configs',
  })

  return (
    <div className={cn('space-y-4', standalone && 'space-y-5')}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div className="space-y-1.5">
          <h3 className="flex items-center gap-2 text-base font-semibold sm:text-lg">
            <span className="bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 inline-flex size-8 items-center justify-center rounded-lg">
              <Link2 className="size-4" />
            </span>
            {t('settings.motherConfigs.title', { defaultValue: 'Mother configs' })}
          </h3>
          <p className="text-muted-foreground max-w-2xl text-xs leading-relaxed sm:text-sm">
            {t('settings.motherConfigs.description', {
              defaultValue:
                'Foreign share links (another panel/IP). Each user only receives them while their own remaining volume on this panel allows it — the remote pool is not treated as unlimited for everyone.',
            })}
          </p>
        </div>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="cursor-pointer shrink-0"
          onClick={() => append({ name: '', link: '', enabled: true, respect_user_quota: true, personalize: false })}
        >
          <Plus className="size-4" />
          {t('settings.motherConfigs.add', { defaultValue: 'Add mother config' })}
        </Button>
      </div>

      {fields.length === 0 ? (
        <div className="border-border/70 bg-muted/15 rounded-2xl border border-dashed px-4 py-10 text-center">
          <p className="text-muted-foreground text-xs sm:text-sm">
            {t('settings.motherConfigs.empty', {
              defaultValue: 'No mother configs yet. Add a vless:// link from another panel.',
            })}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {fields.map((field, index) => (
            <ExternalConfigCard key={field.id} form={form} index={index} onRemove={() => remove(index)} t={t} />
          ))}
        </div>
      )}
    </div>
  )
}
