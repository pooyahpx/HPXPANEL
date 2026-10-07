import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { PulseProfileOption } from '@/service/api/hpx-pulse'
import { Check, Gauge, Radio, Shield, Sparkles, Waves, Zap } from 'lucide-react'
import { useTranslation } from 'react-i18next'

type Props = {
  profiles: PulseProfileOption[]
  recommendedId: string | null
  selectedId: string | null
  onSelect: (profileId: string) => void
  fa?: boolean
}

const carrierMeta = (carrier?: string | null) => {
  const c = (carrier || '').toLowerCase()
  if (c.includes('stealth')) return { icon: Shield, tone: 'text-emerald-400', ring: 'from-emerald-500/25' }
  if (c.includes('wss') || c.includes('ws')) return { icon: Waves, tone: 'text-sky-400', ring: 'from-sky-500/25' }
  if (c.includes('kcp')) return { icon: Radio, tone: 'text-amber-400', ring: 'from-amber-500/25' }
  if (c.includes('quic') || c.includes('udp')) return { icon: Zap, tone: 'text-violet-400', ring: 'from-violet-500/25' }
  return { icon: Gauge, tone: 'text-primary', ring: 'from-primary/25' }
}

const scoreTone = (score: number) => {
  if (score >= 90) return 'bg-emerald-500'
  if (score >= 75) return 'bg-sky-500'
  if (score >= 60) return 'bg-amber-500'
  return 'bg-orange-500'
}

export function RankedTunnelPresets({ profiles, recommendedId, selectedId, onSelect, fa }: Props) {
  const { t } = useTranslation()
  const activeId = selectedId ?? recommendedId
  const top = profiles.slice(0, 10)

  return (
    <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-b from-white/[0.06] to-white/[0.02] p-3 sm:p-4">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-primary/50 to-transparent" />
      <div className="pointer-events-none absolute -top-16 right-0 size-40 rounded-full bg-primary/10 blur-3xl" />

      <div className="relative mb-3 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-foreground flex items-center gap-2 text-sm font-semibold tracking-tight">
            <span className="bg-primary/15 text-primary inline-flex size-7 items-center justify-center rounded-lg">
              <Sparkles className="size-3.5" />
            </span>
            {t('hpxPulse.topProfiles', { defaultValue: 'Ranked tunnel presets' })}
          </div>
          <p className="text-muted-foreground mt-1.5 text-[11px] leading-relaxed">
            {t('hpxPulse.topProfilesHint', {
              defaultValue:
                'TCP Extreme keeps the TCP carrier when Reality needs it. Stealth ranks first for Hard/Mobile; pick Fast to surface UDP family.',
            })}
          </p>
        </div>
        <Badge variant="outline" className="shrink-0 border-white/10 bg-white/5 text-[10px] tracking-wide uppercase">
          {top.length} {t('hpxPulse.profiles', { defaultValue: 'profiles' })}
        </Badge>
      </div>

      <div className="relative max-h-[22rem] space-y-2 overflow-y-auto pe-1">
        {top.map((p, index) => {
          const selected = activeId === p.profile_id
          const recommended = recommendedId === p.profile_id
          const meta = carrierMeta(p.carrier)
          const Icon = meta.icon
          const title = fa ? p.title_fa : p.title
          const reason = (fa ? p.reasons_fa[0] : p.reasons[0]) || ''

          return (
            <button
              key={p.profile_id}
              type="button"
              onClick={() => onSelect(p.profile_id)}
              className={cn(
                'group relative w-full cursor-pointer overflow-hidden rounded-xl border p-3 text-start transition-all duration-200',
                'hover:-translate-y-0.5 hover:border-primary/40 hover:bg-white/[0.04]',
                selected
                  ? 'border-primary/60 bg-primary/10 shadow-[0_0_0_1px_hsl(var(--primary)/0.25),0_12px_40px_-24px_hsl(var(--primary)/0.8)]'
                  : 'border-white/8 bg-black/20',
              )}
            >
              <div
                className={cn(
                  'pointer-events-none absolute inset-y-0 start-0 w-1 bg-gradient-to-b to-transparent opacity-0 transition-opacity',
                  meta.ring,
                  selected && 'opacity-100',
                )}
              />

              <div className="flex items-start gap-3">
                <div
                  className={cn(
                    'mt-0.5 flex size-9 shrink-0 flex-col items-center justify-center rounded-xl border border-white/10 bg-white/[0.04] text-[11px] font-bold tabular-nums',
                    selected && 'border-primary/40 bg-primary/15 text-primary',
                  )}
                >
                  #{index + 1}
                </div>

                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={cn('inline-flex size-6 items-center justify-center rounded-md bg-white/[0.04]', meta.tone)}>
                      <Icon className="size-3.5" />
                    </span>
                    <span className="text-foreground text-[13px] font-semibold tracking-tight">{title}</span>
                    {recommended && (
                      <Badge className="h-5 border-0 bg-emerald-500/15 px-1.5 text-[10px] text-emerald-400 uppercase">
                        {t('hpxPulse.recommended', { defaultValue: 'Best fit' })}
                      </Badge>
                    )}
                    {selected && (
                      <span className="text-primary ms-auto inline-flex items-center gap-1 text-[10px] font-medium">
                        <Check className="size-3" />
                        {t('selected', { defaultValue: 'Selected' })}
                      </span>
                    )}
                  </div>

                  {reason ? <p className="text-muted-foreground mt-1.5 line-clamp-2 text-[11px] leading-relaxed">{reason}</p> : null}

                  <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
                    <Badge variant="outline" className="h-5 border-white/10 bg-white/[0.03] text-[10px] uppercase">
                      {p.preset}
                    </Badge>
                    {p.mss ? (
                      <Badge variant="outline" className="h-5 border-white/10 bg-white/[0.03] text-[10px] uppercase">
                        MSS {p.mss}
                      </Badge>
                    ) : null}
                    {p.carrier ? (
                      <Badge variant="outline" className={cn('h-5 border-white/10 bg-white/[0.03] text-[10px] uppercase', meta.tone)}>
                        {p.carrier}
                      </Badge>
                    ) : null}
                    <div className="ms-auto flex items-center gap-2">
                      <div className="bg-muted/50 h-1.5 w-16 overflow-hidden rounded-full">
                        <div className={cn('h-full rounded-full transition-all', scoreTone(p.score))} style={{ width: `${Math.min(100, p.score)}%` }} />
                      </div>
                      <span className="font-mono text-[11px] font-semibold tabular-nums">{p.score}</span>
                    </div>
                  </div>
                </div>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
