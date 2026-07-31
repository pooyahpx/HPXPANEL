import useDirDetection from '@/hooks/use-dir-detection'
import { cn } from '@/lib/utils'
import { type SystemUsersStats, useGetSystemUsersStats } from '@/service/api'
import { RadioTower, UserCheck, Users } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Card, CardTitle } from '@/components/ui/card'
import { CountUp } from '@/components/ui/count-up'

const UsersStatistics = () => {
  const { t } = useTranslation()
  const dir = useDirDetection()
  const [prevData, setPrevData] = useState<SystemUsersStats | null>(null)
  const [isIncreased, setIsIncreased] = useState<Record<string, boolean>>({})

  const { data } = useGetSystemUsersStats(undefined, {
    query: {
      refetchInterval: 5000,
    },
  })

  useEffect(() => {
    if (prevData && data) {
      setIsIncreased({
        online_users: data.online_users > prevData.online_users,
        active_users: data.active_users > prevData.active_users,
        total_user: data.total_user > prevData.total_user,
      })
    }
    setPrevData(data ?? null)
  }, [data])

  return (
    <div className={cn('grid w-full grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4', dir === 'rtl' && 'xl:grid-flow-col-reverse')}>
      <Card dir={dir} className="group relative min-h-40 overflow-hidden rounded-none p-5 sm:col-span-2 xl:col-span-2">
        <div className="from-primary/18 absolute inset-0 bg-linear-to-br via-transparent to-emerald-400/8" />
        <div className="absolute top-4 right-4 font-mono text-[10px] tracking-[0.14em] text-emerald-400 uppercase">Live presence</div>
        <div className="relative z-10 flex h-full items-end justify-between gap-6">
          <div>
            <div className="mb-5 flex items-center gap-3">
              <span className={cn(data?.online_users ? 'online-beacon' : 'bg-muted-foreground/50 block h-2.5 w-2.5 rounded-full')} />
              <CardTitle className="text-base">{t('statistics.onlineUsers')}</CardTitle>
            </div>
            <span
              className={cn('font-display block text-6xl leading-none font-bold tracking-tighter transition-all duration-500 sm:text-7xl', isIncreased.online_users && 'animate-zoom-out')}
              style={{ animationDuration: '400ms' }}
            >
              {data ? <CountUp end={data.online_users} /> : 0}
            </span>
          </div>
          <RadioTower className="text-primary h-16 w-16 opacity-70 transition-transform duration-300 group-hover:scale-105" strokeWidth={1.25} />
        </div>
      </Card>

      <Card dir={dir} className="group relative min-h-40 overflow-hidden rounded-none p-5">
        <div className="bg-primary absolute inset-x-0 top-0 h-1" />
        <div className="relative z-10 flex h-full flex-col justify-between">
          <div className="flex items-center justify-between gap-3">
            <CardTitle className="text-sm">{t('statistics.activeUsers')}</CardTitle>
            <UserCheck className="text-primary status-live h-5 w-5" />
          </div>
          <span
            className={cn('font-display text-5xl leading-none font-bold tracking-tighter transition-all duration-500', isIncreased.active_users && 'animate-zoom-out')}
            style={{ animationDuration: '400ms' }}
          >
            {data ? <CountUp end={data.active_users} /> : 0}
          </span>
          <span className="text-muted-foreground font-mono text-[10px] tracking-[0.12em] uppercase">Provisioned access</span>
        </div>
      </Card>

      <Card dir={dir} className="group relative min-h-40 overflow-hidden rounded-none p-5">
        <div className="absolute inset-y-0 left-0 w-1 bg-cyan-400" />
        <div className="relative z-10 flex h-full flex-col justify-between">
          <div className="flex items-center justify-between gap-3">
            <CardTitle className="text-sm">{t('statistics.users')}</CardTitle>
            <Users className="h-5 w-5 text-cyan-400" />
          </div>
          <span
            className={cn('font-display text-5xl leading-none font-bold tracking-tighter transition-all duration-500', isIncreased.total_user && 'animate-zoom-out')}
            style={{ animationDuration: '400ms' }}
          >
            {data ? <CountUp end={data.total_user} /> : 0}
          </span>
          <span className="text-muted-foreground font-mono text-[10px] tracking-[0.12em] uppercase">Identity registry</span>
        </div>
      </Card>
    </div>
  )
}

export default UsersStatistics
