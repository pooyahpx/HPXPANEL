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
    <div
      className={cn(
        'relative overflow-hidden rounded-2xl border border-violet-500/20 bg-violet-950/40 p-3.5 shadow-[0_12px_32px_-20px_rgba(109,40,217,0.55)]',
        className,
      )}
    >
      <button
        type="button"
        className="text-sidebar-foreground/45 hover:text-sidebar-foreground absolute top-2.5 right-2.5 rounded-md p-1 transition-colors"
        onClick={() => setDismissed(true)}
        aria-label={t('close', { defaultValue: 'Close' })}
      >
        <X className="h-3.5 w-3.5" />
      </button>
      <div className="flex items-start gap-3 pr-5">
        <CircularProgress value={progress} size={44} strokeWidth={4} showValue={false} className="shrink-0 text-violet-400" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold tracking-tight text-sidebar-foreground">{title}</p>
          <p className="text-sidebar-foreground/55 mt-0.5 text-xs leading-relaxed">{description}</p>
          {confirmLabel && onConfirm && (
            <Button
              size="sm"
              className="mt-3 h-8 w-full rounded-full bg-violet-600 text-xs font-semibold text-white hover:bg-violet-500"
              onClick={onConfirm}
            >
              {confirmLabel}
            </Button>
          )}
        </div>
      </div>
    </div>
  )
}
