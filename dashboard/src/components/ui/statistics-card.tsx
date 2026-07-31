import NumberFlow from '@number-flow/react'
import { motion } from 'framer-motion'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'
import type { SystemUsersStats } from '@/service/api'

const candyCss = `
.candy-bg {
  background-color: hsl(var(--muted) / 0.35);
  background-image: linear-gradient(
    135deg,
    hsl(var(--border) / 0.55) 25%,
    transparent 25.5%,
    transparent 50%,
    hsl(var(--border) / 0.55) 50.5%,
    hsl(var(--border) / 0.55) 75%,
    transparent 75.5%,
    transparent
  );
  background-size: 10px 10px;
}`

export type StatsBarItem = {
  value: number
  label: string
  className?: string
  showToolTip?: boolean
  delay?: number
  suffix?: string
  tooltip?: string
}

type BarChartProps = StatsBarItem

const BarChart = ({
  value,
  label,
  className = '',
  showToolTip = false,
  delay = 0,
  suffix = '%',
  tooltip,
}: BarChartProps) => {
  const clamped = Math.max(0, Math.min(100, value))

  return (
    <div className="group relative h-full w-full">
      <div className="candy-bg relative h-full w-full overflow-hidden rounded-[28px] sm:rounded-[36px]">
        <motion.div
          initial={{ opacity: 0, y: 100, height: 0 }}
          animate={{ opacity: 1, y: 0, height: `${clamped}%` }}
          transition={{ duration: 0.5, type: 'spring', damping: 20, delay }}
          className={cn('absolute bottom-0 mt-auto w-full rounded-[28px] bg-primary/80 p-2 text-primary-foreground sm:rounded-[36px] sm:p-3', className)}
        >
          <div className="relative flex h-10 w-full items-center justify-center gap-1 rounded-full bg-muted/20 text-sm tracking-tighter sm:h-12 sm:text-base">
            <NumberFlow value={Math.round(clamped)} suffix={suffix} />
          </div>
        </motion.div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 100, height: 0 }}
        animate={{ opacity: 1, y: 0, height: `${clamped}%` }}
        transition={{ duration: 0.5, type: 'spring', damping: 15, delay }}
        className="absolute bottom-0 w-full"
      >
        <motion.div
          initial={{ opacity: 0, y: 100 }}
          animate={{ opacity: showToolTip ? 1 : 0, y: showToolTip ? 0 : 100 }}
          transition={{ duration: 0.5, type: 'spring', damping: 15, delay }}
          className={cn(
            'absolute -top-9 left-1/2 -translate-x-1/2 -translate-y-1/2 rounded-xl bg-muted-foreground px-2 py-1 text-xs whitespace-nowrap text-white',
            className,
          )}
        >
          <div
            className={cn(
              'absolute -bottom-9 left-1/2 size-4 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white bg-muted-foreground transition-all duration-300 ease-in-out',
              className,
            )}
          />
          <svg
            className={cn('absolute -bottom-2 left-1/2 -translate-x-1/2', className.includes('bg-') ? 'text-inherit' : 'text-muted-foreground')}
            width="10"
            height="10"
            viewBox="0 0 10 10"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <path
              d="M3.83855 8.41381C4.43827 9.45255 5.93756 9.45255 6.53728 8.41381L9.65582 3.01233C10.2555 1.97359 9.50589 0.675159 8.30646 0.675159H2.06937C0.869935 0.675159 0.120287 1.97359 0.720006 3.01233L3.83855 8.41381Z"
              fill="currentColor"
            />
          </svg>
          {tooltip}
        </motion.div>
      </motion.div>
      <p className="text-muted-foreground/80 mx-auto mt-2 w-fit text-center text-xs tracking-tight sm:text-sm">{label}</p>
    </div>
  )
}

type StatsProps = {
  title?: string
  description?: string
  items: StatsBarItem[]
  className?: string
  chartClassName?: string
}

function Stats({ title, description, items, className, chartClassName }: StatsProps) {
  return (
    <section className={cn('w-full', className)}>
      <style>{candyCss}</style>
      {(title || description) && (
        <div className="mx-auto mb-6 max-w-2xl text-center sm:mb-8">
          {title && <h2 className="font-display text-2xl font-bold tracking-tight sm:text-3xl md:text-4xl">{title}</h2>}
          {description && <p className="text-muted-foreground mt-2 text-sm tracking-tight sm:text-base">{description}</p>}
        </div>
      )}
      <div className={cn('relative mx-auto flex h-72 max-w-4xl items-end justify-center gap-2 sm:h-96 sm:gap-3', chartClassName)}>
        {items.map((props, index) => (
          <motion.div
            key={`${props.label}-${index}`}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{
              duration: 0.5,
              delay: index * 0.12,
              type: 'spring',
              damping: 10,
            }}
            className="h-full w-full min-w-0"
          >
            <BarChart {...props} delay={props.delay ?? index * 0.15} />
          </motion.div>
        ))}
      </div>
    </section>
  )
}

type UserStatsBarsProps = {
  data?: SystemUsersStats
  className?: string
  showHeader?: boolean
}

function UserStatsBars({ data, className, showHeader = true }: UserStatsBarsProps) {
  const { t } = useTranslation()
  const total = data?.total_user ?? 0

  const toPercent = (count: number | undefined) => {
    if (!total || !count) return 0
    return Math.round((count / total) * 100)
  }

  const items: StatsBarItem[] = [
    {
      value: toPercent(data?.active_users),
      label: t('statistics.activeUsers'),
      tooltip: `${data?.active_users ?? 0}`,
      className: 'bg-emerald-500',
      showToolTip: true,
      delay: 0.15,
    },
    {
      value: toPercent(data?.online_users),
      label: t('statistics.onlineUsers'),
      tooltip: `${data?.online_users ?? 0}`,
      className: 'bg-sky-400',
      showToolTip: (data?.online_users ?? 0) > 0,
      delay: 0.3,
    },
    {
      value: toPercent(data?.expired_users),
      label: t('statistics.expiredUsers'),
      tooltip: `${data?.expired_users ?? 0}`,
      className: 'bg-amber-500',
      delay: 0.45,
    },
    {
      value: toPercent(data?.limited_users),
      label: t('statistics.limitedUsers'),
      tooltip: `${data?.limited_users ?? 0}`,
      className: 'bg-rose-500',
      delay: 0.6,
    },
  ]

  return (
    <div className={cn('bg-card/80 rounded-2xl border border-border/70 p-4 shadow-sm backdrop-blur-md sm:p-6', className)}>
      {showHeader && (
        <div className="mb-4 flex flex-wrap items-end justify-between gap-2">
          <div>
            <h3 className="font-display text-lg font-semibold tracking-tight sm:text-xl">{t('statistics.users')}</h3>
            <p className="text-muted-foreground text-xs sm:text-sm">{t('monitorUsers')}</p>
          </div>
          <div className="font-mono text-sm font-semibold sm:text-base">
            <NumberFlow value={total} /> <span className="text-muted-foreground text-xs font-medium">{t('statistics.users')}</span>
          </div>
        </div>
      )}
      <Stats items={items} chartClassName="h-64 sm:h-80" />
    </div>
  )
}

export { Stats, BarChart, UserStatsBars }
