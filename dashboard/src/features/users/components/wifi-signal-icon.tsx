import { cn } from '@/lib/utils'
import { memo } from 'react'

type WifiSignalIconProps = {
  animated?: boolean
  className?: string
}

export const WifiSignalIcon = memo(({ animated = false, className }: WifiSignalIconProps) => (
  <span className={cn('wifi-signal', !animated && '[&>*]:!animate-none [&>*]:!opacity-80', className)} aria-hidden="true">
    <span className="wifi-signal__arc" />
    <span className="wifi-signal__arc" />
    <span className="wifi-signal__arc" />
  </span>
))

WifiSignalIcon.displayName = 'WifiSignalIcon'
