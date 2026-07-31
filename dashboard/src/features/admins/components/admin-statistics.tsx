import useDirDetection from '@/hooks/use-dir-detection'
import { cn } from '@/lib/utils.ts'
import { useTranslation } from 'react-i18next'
import { Card, CardTitle } from '@/components/ui/card'
import { CountUp } from '@/components/ui/count-up'
import { User, UserCheck, UserLock, UserX } from 'lucide-react'
import React, { useEffect, useState } from 'react'

interface AdminsStatisticsProps {
  counts: { total: number; active: number; disabled: number; limited: number } | null
}

export default function AdminStatisticsSection({ counts }: AdminsStatisticsProps) {
  const { t } = useTranslation()
  const dir = useDirDetection()
  const [prevStats, setPrevStats] = useState<{ total: number; active: number; disabled: number; limited: number } | null>(null)
  const [isIncreased, setIsIncreased] = useState<Record<string, boolean>>({})

  const total = counts?.total || 0
  const active = counts?.active || 0
  const disabled = counts?.disabled || 0
  const limited = counts?.limited || 0

  const currentStats = { total, active, disabled, limited }

  useEffect(() => {
    if (prevStats) {
      setIsIncreased({
        total: currentStats.total > prevStats.total,
        active: currentStats.active > prevStats.active,
        disabled: currentStats.disabled > prevStats.disabled,
        limited: currentStats.limited > prevStats.limited,
      })
    }
    setPrevStats(currentStats)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [counts])

  const stats = [
    {
      icon: User,
      label: t('admins.total'),
      value: total,
      color: '',
      key: 'total',
    },
    {
      icon: UserCheck,
      label: t('admins.active'),
      value: active,
      color: '',
      key: 'active',
    },
    {
      icon: UserX,
      label: t('admins.disable'),
      value: disabled,
      color: '',
      key: 'disabled',
    },
    {
      icon: UserLock,
      label: t('admins.limited'),
      value: limited,
      color: '',
      key: 'limited',
    },
  ]

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4" dir={dir} aria-label={t('admins.statistics', { defaultValue: 'Administrator telemetry' })}>
      {stats.map((stat, idx) => (
        <Card
          key={stat.label}
          dir={dir}
          className="group animate-fade-in relative w-full overflow-hidden transition-colors duration-300"
          style={{
            animationDuration: '600ms',
            animationDelay: `${(idx + 1) * 100}ms`,
            animationFillMode: 'both',
          }}
        >
          <div
            className={cn(
              'from-primary/10 absolute inset-0 bg-gradient-to-r to-transparent opacity-0 transition-opacity duration-500',
              'dark:from-primary/5 dark:to-transparent',
              'group-hover:opacity-100',
            )}
          />
          <CardTitle className="relative z-10 flex items-center justify-between gap-4 px-4 py-4">
            <div className="flex min-w-0 items-center gap-3">
              <span className="border-border text-primary flex h-8 w-8 shrink-0 items-center justify-center border" aria-hidden="true">
                {React.createElement(stat.icon, { className: 'h-4 w-4' })}
              </span>
              <span className="truncate font-mono text-[10px] font-bold tracking-[0.1em] uppercase">{stat.label}</span>
            </div>
            <span className={cn('font-display text-2xl font-bold tabular-nums transition-all duration-500', isIncreased[stat.key] ? 'animate-zoom-out' : '')} style={{ animationDuration: '400ms' }}>
              <CountUp end={stat.value} />
            </span>
          </CardTitle>
        </Card>
      ))}
    </div>
  )
}
