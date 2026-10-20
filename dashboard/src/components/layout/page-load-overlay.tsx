import { useEffect, useRef, useState } from 'react'
import { GooeyLoader } from '@/components/ui/loader-10'
import { cn } from '@/lib/utils'
import { useTranslation } from 'react-i18next'

const MIN_VISIBLE_MS = 2000

/** Electric blue / ink — premium ops splash (not pink). */
const GOOEY_THEME = {
  primaryColor: '#38bdf8',
  secondaryColor: '#1e3a8a',
  borderColor: '#e2e8f0',
} as const

/**
 * Full-screen gooey loader centered on first dashboard mount.
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
        'fixed inset-0 z-[100] flex flex-col items-center justify-center bg-[#05070c]/92 backdrop-blur-md transition-opacity duration-300',
        fading ? 'opacity-0' : 'opacity-100',
      )}
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <GooeyLoader {...GOOEY_THEME} className="scale-110 sm:scale-125" />
      <p className="mt-8 text-sm font-medium tracking-[0.18em] text-slate-300 uppercase">{t('loading')}</p>
    </div>
  )
}
