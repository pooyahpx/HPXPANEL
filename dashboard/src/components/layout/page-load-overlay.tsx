import { useEffect, useRef, useState } from 'react'
import { GooeyLoader } from '@/components/ui/loader-10'
import { cn } from '@/lib/utils'
import { useTranslation } from 'react-i18next'

const SPLASH_KEY = 'hpx.splash.shown.v1'
const MIN_VISIBLE_MS = 1400

/** Electric blue / ink — premium ops splash. */
const GOOEY_THEME = {
  primaryColor: '#38bdf8',
  secondaryColor: '#1e3a8a',
  borderColor: '#94a3b8',
} as const

function splashAlreadyShown() {
  try {
    return sessionStorage.getItem(SPLASH_KEY) === '1'
  } catch {
    return false
  }
}

function markSplashShown() {
  try {
    sessionStorage.setItem(SPLASH_KEY, '1')
  } catch {
    /* ignore */
  }
}

/**
 * Full-screen gooey splash — once per browser tab session only.
 * Route transitions use TopLoadingBar / lightweight LoadingSpinner (no second gooey).
 */
export function PageLoadOverlay({ minDurationMs = MIN_VISIBLE_MS }: { minDurationMs?: number }) {
  const { t } = useTranslation()
  const [visible, setVisible] = useState(() => !splashAlreadyShown())
  const [fading, setFading] = useState(false)
  const hideTimer = useRef<number | null>(null)
  const fadeTimer = useRef<number | null>(null)

  useEffect(() => {
    if (!visible) return

    markSplashShown()
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
  }, [minDurationMs, visible])

  if (!visible) return null

  return (
    <div
      className={cn(
        'fixed inset-0 z-[100] flex flex-col items-center justify-center bg-[#05070c]/94 backdrop-blur-md transition-opacity duration-300',
        fading ? 'opacity-0' : 'opacity-100',
      )}
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <GooeyLoader {...GOOEY_THEME} className="scale-100 sm:scale-110" />
      <p className="mt-7 text-xs font-medium tracking-[0.2em] text-slate-400 uppercase sm:text-sm">{t('loading')}</p>
    </div>
  )
}
