import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { fetcher } from '@/service/http'
import { Activity, Gauge, RefreshCw, Users, Zap } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

export type MotherConfigUsage = {
  total_users: number
  active_users: number
  on_hold_users: number
  limited_users: number
  expired_users: number
  disabled_users: number
  eligible_for_quota_gated: number
  exhausted_volume: number
  unlimited_users: number
  online_users: number
  used_traffic_bytes: number
  data_limit_bytes: number
  remaining_bytes: number
  usage_pct: number
  enabled_configs: number
  total_configs: number
  personalized_configs: number
  configs: Array<{
    name: string
    enabled: boolean
    respect_user_quota: boolean
    personalize: boolean
    eligible_users: number
    gated_by_quota: number
    gated_by_status: number
    online_users: number
  }>
}

function formatBytes(n: number): string {
  if (!Number.isFinite(n) || n <= 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let v = n
  let i = 0
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024
    i += 1
  }
  return `${v.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

function StatTile({
  label,
  value,
  hint,
  accent,
}: {
  label: string
  value: string
  hint?: string
  accent?: 'emerald' | 'sky' | 'amber' | 'rose'
}) {
  const ring =
    accent === 'sky'
      ? 'border-sky-500/30 from-sky-500/15'
      : accent === 'amber'
        ? 'border-amber-500/30 from-amber-500/15'
        : accent === 'rose'
          ? 'border-rose-500/30 from-rose-500/15'
          : 'border-emerald-500/30 from-emerald-500/15'
  return (
    <div className={cn('rounded-2xl border bg-gradient-to-br to-transparent px-3.5 py-3', ring)}>
      <p className="text-muted-foreground text-[10px] font-semibold tracking-[0.14em] uppercase">{label}</p>
      <p className="mt-1.5 font-mono text-lg font-semibold tabular-nums tracking-tight">{value}</p>
      {hint ? <p className="text-muted-foreground mt-1 text-[11px] leading-snug">{hint}</p> : null}
    </div>
  )
}

export function MotherConfigUsagePanel() {
  const { t } = useTranslation()
  const [data, setData] = useState<MotherConfigUsage | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetcher<MotherConfigUsage>('/api/settings/subscription/external-configs/usage')
      setData(res)
    } catch (error: any) {
      toast.error(
        error?.data?.detail ||
          error?.message ||
          t('settings.motherConfigs.usageLoadFailed', { defaultValue: 'Failed to load consumption' }),
      )
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <section className="from-sky-500/10 via-background to-orange-500/5 relative overflow-hidden rounded-2xl border border-white/5 bg-gradient-to-br p-4 sm:p-6">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,rgba(56_189_248/0.18),transparent_55%)]" />
      <div className="relative space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <Gauge className="text-sky-500 size-4" />
              <h2 className="text-sm font-semibold">
                {t('settings.motherConfigs.usageTitle', { defaultValue: 'Mother config consumption' })}
              </h2>
              <Badge variant="outline" className="h-5 text-[10px]">
                {t('settings.motherConfigs.usageLive', { defaultValue: 'Live panel volume' })}
              </Badge>
            </div>
            <p className="text-muted-foreground max-w-2xl text-xs leading-relaxed">
              {t('settings.motherConfigs.usageHint', {
                defaultValue:
                  'Eligible + online users for mother configs. With “Bind local user UUID” on, traffic on a mother Node counts against each user’s volume.',
              })}
            </p>
          </div>
          <Button type="button" size="sm" variant="outline" className="cursor-pointer h-8 gap-1.5" onClick={() => void load()} disabled={loading}>
            <RefreshCw className={cn('size-3.5', loading && 'animate-spin')} />
            {t('refresh', { defaultValue: 'Refresh' })}
          </Button>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile
            label={t('settings.motherConfigs.usageEligible', { defaultValue: 'Eligible users' })}
            value={loading ? '—' : String(data?.eligible_for_quota_gated ?? 0)}
            hint={t('settings.motherConfigs.usageEligibleHint', {
              defaultValue: 'Active/on-hold with remaining volume',
            })}
            accent="emerald"
          />
          <StatTile
            label={t('settings.motherConfigs.usageExhausted', { defaultValue: 'Volume exhausted' })}
            value={loading ? '—' : String(data?.exhausted_volume ?? 0)}
            hint={t('settings.motherConfigs.usageExhaustedHint', {
              defaultValue: 'Gated when “Respect user volume” is on',
            })}
            accent="amber"
          />
          <StatTile
            label={t('settings.motherConfigs.usageUsed', { defaultValue: 'Used traffic' })}
            value={loading ? '—' : formatBytes(data?.used_traffic_bytes ?? 0)}
            hint={
              loading
                ? undefined
                : t('settings.motherConfigs.usageRemaining', {
                    defaultValue: '{{remaining}} remaining on limited plans',
                    remaining: formatBytes(data?.remaining_bytes ?? 0),
                  })
            }
            accent="sky"
          />
          <StatTile
            label={t('settings.motherConfigs.usagePct', { defaultValue: 'Limited plan fill' })}
            value={loading ? '—' : `${data?.usage_pct ?? 0}%`}
            hint={t('settings.motherConfigs.usagePctHint', {
              defaultValue: 'Across users with a data limit',
            })}
            accent="rose"
          />
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="bg-background/40 flex items-center gap-2 rounded-xl border px-3 py-2 text-xs">
            <Users className="text-muted-foreground size-3.5" />
            <span className="text-muted-foreground">{t('settings.motherConfigs.usageActive', { defaultValue: 'Active' })}</span>
            <span className="ms-auto font-mono font-semibold">{loading ? '—' : data?.active_users ?? 0}</span>
          </div>
          <div className="bg-background/40 flex items-center gap-2 rounded-xl border border-emerald-500/20 px-3 py-2 text-xs">
            <Activity className="size-3.5 text-emerald-500" />
            <span className="text-muted-foreground">{t('settings.motherConfigs.usageOnline', { defaultValue: 'Online now' })}</span>
            <span className="ms-auto font-mono font-semibold text-emerald-600 dark:text-emerald-400">
              {loading ? '—' : data?.online_users ?? 0}
            </span>
          </div>
          <div className="bg-background/40 flex items-center gap-2 rounded-xl border px-3 py-2 text-xs">
            <Zap className="text-muted-foreground size-3.5" />
            <span className="text-muted-foreground">{t('settings.motherConfigs.usageUnlimited', { defaultValue: 'Unlimited' })}</span>
            <span className="ms-auto font-mono font-semibold">{loading ? '—' : data?.unlimited_users ?? 0}</span>
          </div>
          <div className="bg-background/40 flex items-center gap-2 rounded-xl border px-3 py-2 text-xs">
            <Activity className="text-muted-foreground size-3.5" />
            <span className="text-muted-foreground">{t('settings.motherConfigs.usageConfigs', { defaultValue: 'Enabled configs' })}</span>
            <span className="ms-auto font-mono font-semibold">
              {loading ? '—' : `${data?.enabled_configs ?? 0}/${data?.total_configs ?? 0}`}
            </span>
          </div>
        </div>

        {!loading && data && data.configs.length > 0 ? (
          <div className="overflow-hidden rounded-xl border">
            <div className="bg-muted/40 text-muted-foreground grid grid-cols-[minmax(0,1.5fr)_repeat(4,minmax(0,0.55fr))] gap-2 px-3 py-2 text-[10px] font-semibold tracking-wide uppercase">
              <span>{t('settings.motherConfigs.name', { defaultValue: 'Display name' })}</span>
              <span className="text-end">{t('settings.motherConfigs.usageColEligible', { defaultValue: 'Eligible' })}</span>
              <span className="text-end">{t('settings.motherConfigs.usageColOnline', { defaultValue: 'Online' })}</span>
              <span className="text-end">{t('settings.motherConfigs.usageColQuota', { defaultValue: 'Quota gate' })}</span>
              <span className="text-end">{t('settings.motherConfigs.usageColStatus', { defaultValue: 'Status gate' })}</span>
            </div>
            <ul className="divide-border divide-y">
              {data.configs.map((cfg, i) => (
                <li
                  key={`${cfg.name}-${i}`}
                  className={cn(
                    'grid grid-cols-[minmax(0,1.5fr)_repeat(4,minmax(0,0.55fr))] items-center gap-2 px-3 py-2.5 text-sm',
                    !cfg.enabled && 'opacity-50',
                  )}
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium">{cfg.name || t('settings.motherConfigs.unnamed', { defaultValue: 'Untitled config' })}</p>
                    <p className="text-muted-foreground text-[11px]">
                      {!cfg.enabled
                        ? t('disabled', { defaultValue: 'Disabled' })
                        : [
                            cfg.personalize
                              ? t('settings.motherConfigs.personalizeOn', { defaultValue: 'Bound UUID' })
                              : t('settings.motherConfigs.personalizeOff', { defaultValue: 'Shared UUID' }),
                            cfg.respect_user_quota
                              ? t('settings.motherConfigs.respectQuota', { defaultValue: 'Respect user volume' })
                              : t('settings.motherConfigs.usageAlwaysOn', { defaultValue: 'Always on for active users' }),
                          ].join(' · ')}
                    </p>
                  </div>
                  <span className="text-end font-mono tabular-nums">{cfg.eligible_users}</span>
                  <span className="text-end font-mono tabular-nums text-emerald-600 dark:text-emerald-400">{cfg.online_users}</span>
                  <span className="text-end font-mono tabular-nums text-amber-600 dark:text-amber-400">{cfg.gated_by_quota}</span>
                  <span className="text-end font-mono tabular-nums text-rose-600 dark:text-rose-400">{cfg.gated_by_status}</span>
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </div>
    </section>
  )
}
