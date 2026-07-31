import { useEffect, useRef, useState } from 'react'
import { GradientLoader } from '@/components/ui/gradient-loader'
import { cn } from '@/lib/utils'
import { useTranslation } from 'react-i18next'

const MIN_VISIBLE_MS = 2000

/**
 * Full-screen gradient loader shown only on the first dashboard mount.
 * Sidebar / in-app navigations use TopLoadingBar instead — no overlay.
 */
export function PageLoadOverlay({ minDurationMs = MIN_VISIBLE_MS }: { minDurationMs?: number }) {
  const { t } = useTranslation()
  const [visible, setVisible] = useState(true)
  const [fading, setFading] = useState(false)
  const hideTimer = useRef<number | null>(null)
  const fadeTimer = useRef<number | null>(null)

  useEffect(() => {
    const shownAt = Date.now()
    hideTimer.current = window.setTimeout(() => {
      setFading(true)
      fadeTimer.current = window.setTimeout(() => {
        setVisible(false)
        setFading(false)
      }, 280)
    }, Math.max(0, minDurationMs - (Date.now() - shownAt)))

    return () => {
      if (hideTimer.current) window.clearTimeout(hideTimer.current)
      if (fadeTimer.current) window.clearTimeout(fadeTimer.current)
    }
  }, [minDurationMs])

  if (!visible) return null

  return (
    <div
      className={cn(
        'bg-background/85 fixed inset-0 z-[100] flex flex-col items-center justify-center backdrop-blur-md transition-opacity duration-300',
        fading ? 'opacity-0' : 'opacity-100',
      )}
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <GradientLoader size={96} />
      <p className="text-muted-foreground mt-6 text-sm font-medium tracking-wide">{t('loading')}</p>
    </div>
  )
}
