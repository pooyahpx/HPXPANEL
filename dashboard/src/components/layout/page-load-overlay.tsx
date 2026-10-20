import { useEffect, useRef, useState } from 'react'
import { HpxRecLoader } from '@/components/ui/loader-6'
import { cn } from '@/lib/utils'
import { useTranslation } from 'react-i18next'

const SPLASH_KEY = 'hpx.splash.shown.v2'
const MIN_VISIBLE_MS = 3000

/** Deep blue + navy ink for the HPX splash. */
const HPX_LOADER_THEME = {
  accentColor: '#2563eb',
  inkColor: '#020617',
  label: 'HPX',
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
 * Full-screen HPX morph splash — once per browser tab session.
 * Route transitions keep the lightweight LoadingSpinner.
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
        'fixed inset-0 z-[100] flex flex-col items-center justify-center bg-[#020617]/96 backdrop-blur-md transition-opacity duration-300',
        fading ? 'opacity-0' : 'opacity-100',
      )}
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <HpxRecLoader {...HPX_LOADER_THEME} className="scale-90 sm:scale-100" />
      <p className="mt-4 text-xs font-medium tracking-[0.22em] text-slate-400 uppercase sm:text-sm">{t('loading')}</p>
    </div>
  )
}
