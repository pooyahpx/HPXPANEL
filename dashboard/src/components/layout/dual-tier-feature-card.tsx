import { X } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { CircularProgress } from '@/components/ui/circular-progress'

type DualTierFeatureCardProps = {
  title: string
  description: string
  progress: number
  confirmLabel?: string
  onConfirm?: () => void
  className?: string
}

export function DualTierFeatureCard({ title, description, progress, confirmLabel, onConfirm, className }: DualTierFeatureCardProps) {
  const { t } = useTranslation()
  const [dismissed, setDismissed] = useState(false)
  if (dismissed) return null

  return (
    <div className={cn('border-sidebar-border bg-sidebar-accent/40 relative overflow-hidden rounded-none border p-3 shadow-[2px_2px_0_0_hsl(var(--pixel-border)/0.35)]', className)}>
      <button
        type="button"
        className="text-sidebar-foreground/50 hover:text-sidebar-foreground absolute top-2 right-2 rounded-md p-1"
        onClick={() => setDismissed(true)}
        aria-label={t('close', { defaultValue: 'Close' })}
      >
        <X className="h-3.5 w-3.5" />
      </button>
      <div className="flex items-start gap-3 pr-4">
        <CircularProgress value={progress} size={42} strokeWidth={4} showValue={false} className="shrink-0" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold tracking-tight">{title}</p>
          <p className="text-sidebar-foreground/60 mt-1 text-xs leading-relaxed">{description}</p>
          {confirmLabel && onConfirm && (
            <Button size="sm" className="mt-3 h-8 w-full rounded-xl text-xs" onClick={onConfirm}>
              {confirmLabel}
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
