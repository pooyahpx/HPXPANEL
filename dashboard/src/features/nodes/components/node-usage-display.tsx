import useDirDetection from '@/hooks/use-dir-detection'
import { cn } from '@/lib/utils'
import { Progress } from '@/components/ui/progress'
import { formatBytes } from '@/utils/formatByte'
import { NodeResponse } from '@/service/api'
import { Download, Gauge, HardDrive, Upload } from 'lucide-react'
import { statusColors } from '@/constants/UserSettings'
import { useTranslation } from 'react-i18next'

interface NodeUsageDisplayProps {
  node: NodeResponse
}

export default function NodeUsageDisplay({ node }: NodeUsageDisplayProps) {
  const { t } = useTranslation()
  const isRTL = useDirDetection() === 'rtl'
  const uplink = node.uplink || 0
  const downlink = node.downlink || 0
  const totalUsed = uplink + downlink
  const lifetimeUplink = node.lifetime_uplink || 0
  const lifetimeDownlink = node.lifetime_downlink || 0
  const totalLifetime = lifetimeUplink + lifetimeDownlink
  const dataLimit = node.data_limit
  const isUnlimited = dataLimit === null || dataLimit === undefined || dataLimit === 0
  const progressValue = isUnlimited || !dataLimit ? 0 : Math.min((totalUsed / dataLimit) * 100, 100)

  const getProgressColor = () => {
    if (isUnlimited) return ''
    if (progressValue >= 90) return statusColors.limited.sliderColor
    if (progressValue >= 70) return statusColors.expired.sliderColor
    return statusColors.active.sliderColor
  }

  if (totalUsed === 0 && !dataLimit && totalLifetime === 0) {
    return null
  }

  const tiles = [
    {
      key: 'session',
      label: t('nodes.metrics.session', { defaultValue: 'Session' }),
      value: formatBytes(totalUsed),
      icon: Gauge,
      tone: 'text-foreground',
    },
    {
      key: 'lifetime',
      label: t('nodes.metrics.lifetime', { defaultValue: 'Lifetime' }),
      value: totalLifetime > 0 ? formatBytes(totalLifetime) : '—',
      icon: HardDrive,
      tone: 'text-muted-foreground',
    },
    {
      key: 'up',
      label: t('nodes.metrics.uplink', { defaultValue: 'Uplink' }),
      value: formatBytes(uplink),
      icon: Upload,
      tone: 'text-sky-500 dark:text-sky-400',
    },
    {
      key: 'down',
      label: t('nodes.metrics.downlink', { defaultValue: 'Downlink' }),
      value: formatBytes(downlink),
      icon: Download,
      tone: 'text-emerald-500 dark:text-emerald-400',
    },
  ]

  return (
    <div className={cn('min-w-0 space-y-3', isRTL ? 'text-right' : 'text-left')}>
      {!isUnlimited && dataLimit ? (
        <div className="space-y-1.5">
          <div className="text-muted-foreground flex items-center justify-between gap-2 text-[11px]">
            <span>{t('nodes.metrics.quota', { defaultValue: 'Quota' })}</span>
            <span dir="ltr" className="font-mono tabular-nums">
              {formatBytes(totalUsed)} / {formatBytes(dataLimit)}
            </span>
          </div>
          <Progress value={progressValue} className="h-1.5" indicatorClassName={getProgressColor()} />
        </div>
      ) : null}

      <div className="grid grid-cols-2 gap-2">
        {tiles.map(tile => {
          const Icon = tile.icon
          return (
            <div key={tile.key} className="bg-muted/35 border-border/50 rounded-lg border px-2.5 py-2">
              <div className="text-muted-foreground mb-1 flex items-center gap-1 text-[10px] font-medium tracking-wide uppercase">
                <Icon className={cn('h-3 w-3 shrink-0', tile.tone)} strokeWidth={2.25} />
                <span>{tile.label}</span>
              </div>
              <div dir="ltr" className={cn('truncate text-sm font-semibold tabular-nums', tile.tone)}>
                {tile.value}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
