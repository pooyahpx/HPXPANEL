import { ArrowUpRight, Github, Sparkles, X } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { cn } from '@/lib/utils'
import { getAuthToken } from '@/utils/authStorage'
import { DONATION_URL, REPO_URL } from '@/constants/Project'

const DONATION_STORAGE_KEY = 'donation_popup_data'
const FIRST_SHOW_DELAY = 10 * 60 * 1000 // 10 minutes in milliseconds
const SECRET_SALT = 'hpxpanel_donation_v1' // Simple salt for checksum
const MAX_TIMEOUT_MS = 2_147_483_647 // Browser timeout limit (~24.8 days)

interface DonationData {
  lastShown: string | null
  nextShowTime: string
  showCount: number
  checksum: string
}

// Calculate delay in days based on show count (progressive delays)
const getDelayDays = (showCount: number): number => {
  switch (showCount) {
    case 0:
      return 3 // First show: 3 days
    case 1:
      return 7 // Second show: 7 days
    case 2:
      return 14 // Third show: 14 days
    default:
      return 30 // Fourth show and beyond: 30 days (1 month)
  }
}

// Simple hash function for tamper detection
const generateChecksum = (lastShown: string | null, nextShowTime: string, showCount: number): string => {
  const data = `${lastShown || 'null'}_${nextShowTime}_${showCount}_${SECRET_SALT}`
  let hash = 0
  for (let i = 0; i < data.length; i++) {
    const char = data.charCodeAt(i)
    hash = (hash << 5) - hash + char
    hash = hash & hash // Convert to 32-bit integer
  }
  return Math.abs(hash).toString(36)
}

// Validate data integrity and reasonableness
const validateData = (data: DonationData): boolean => {
  // Check checksum
  const expectedChecksum = generateChecksum(data.lastShown, data.nextShowTime, data.showCount ?? 0)
  if (data.checksum !== expectedChecksum) {
    console.warn('Donation popup: Data tampering detected (checksum mismatch)')
    return false
  }

  // Validate showCount is a non-negative integer
  if (typeof data.showCount !== 'number' || data.showCount < 0 || !Number.isInteger(data.showCount)) {
    console.warn('Donation popup: Invalid showCount')
    return false
  }

  // Validate timestamps are valid dates
  const nextShowTimestamp = new Date(data.nextShowTime).getTime()
  if (isNaN(nextShowTimestamp)) {
    console.warn('Donation popup: Invalid nextShowTime format')
    return false
  }

  if (data.lastShown) {
    const lastShownTimestamp = new Date(data.lastShown).getTime()
    if (isNaN(lastShownTimestamp)) {
      console.warn('Donation popup: Invalid lastShown format')
      return false
    }

    // Validate relationship: nextShowTime should be after lastShown
    if (nextShowTimestamp < lastShownTimestamp) {
      console.warn('Donation popup: nextShowTime is before lastShown')
      return false
    }

    // Validate: nextShowTime should match expected delay based on showCount
    const expectedDelayDays = getDelayDays(data.showCount)
    const maxExpectedNext = lastShownTimestamp + (expectedDelayDays + 1) * 24 * 60 * 60 * 1000 // +1 day buffer
    if (nextShowTimestamp > maxExpectedNext) {
      console.warn('Donation popup: nextShowTime too far in future')
      return false
    }
  }

  // Validate: nextShowTime shouldn't be more than 1 year in the past or future from now
  const now = Date.now()
  const oneYearAgo = now - 365 * 24 * 60 * 60 * 1000
  const oneYearLater = now + 365 * 24 * 60 * 60 * 1000

  if (nextShowTimestamp < oneYearAgo || nextShowTimestamp > oneYearLater) {
    console.warn('Donation popup: nextShowTime outside reasonable range')
    return false
  }

  return true
}

// localStorage helper functions
const setStorageData = (data: Omit<DonationData, 'checksum'>) => {
  const checksum = generateChecksum(data.lastShown, data.nextShowTime, data.showCount ?? 0)
  const fullData: DonationData = { ...data, checksum }
  localStorage.setItem(DONATION_STORAGE_KEY, JSON.stringify(fullData))
}

const getStorageData = (): DonationData | null => {
  const stored = localStorage.getItem(DONATION_STORAGE_KEY)
  if (!stored) return null
  try {
    const data = JSON.parse(stored) as Partial<DonationData>
    // Handle backward compatibility: if showCount is missing, default to 0
    const fullData: DonationData = {
      ...data,
      showCount: data.showCount ?? 0,
    } as DonationData
    // Validate data integrity
    if (!validateData(fullData)) {
      // Tampering detected, clear invalid data
      localStorage.removeItem(DONATION_STORAGE_KEY)
      return null
    }
    return fullData
  } catch {
    return null
  }
}

export default function DonationPopup() {
  const { t } = useTranslation()
  const [isVisible, setIsVisible] = useState(false)
  const [isAnimating, setIsAnimating] = useState(false)
  const timeoutIdsRef = useRef<number[]>([])
  const hasShownRef = useRef(false)

  const clearScheduledTimeouts = useCallback(() => {
    timeoutIdsRef.current.forEach(timeoutId => window.clearTimeout(timeoutId))
    timeoutIdsRef.current = []
  }, [])

  const schedulePopup = useCallback((delayMs: number, callback: () => void) => {
    const scheduleChunk = (remainingMs: number) => {
      const nextDelay = Math.min(remainingMs, MAX_TIMEOUT_MS)
      const timeoutId = window.setTimeout(() => {
        timeoutIdsRef.current = timeoutIdsRef.current.filter(id => id !== timeoutId)
        if (remainingMs > MAX_TIMEOUT_MS) {
          scheduleChunk(remainingMs - MAX_TIMEOUT_MS)
          return
        }
        callback()
      }, nextDelay)
      timeoutIdsRef.current.push(timeoutId)
    }

    if (delayMs <= 0) {
      callback()
      return
    }

    scheduleChunk(delayMs)
  }, [])

  const showPopup = useCallback(() => {
    if (hasShownRef.current) {
      return
    }
    hasShownRef.current = true

    const now = Date.now()
    const data = getStorageData()
    const currentShowCount = data?.showCount ?? 0

    // Calculate next delay based on current show count
    const delayDays = getDelayDays(currentShowCount)
    const nextShowTime = new Date(now + delayDays * 24 * 60 * 60 * 1000).toISOString()

    // Update storage: increment showCount and set nextShowTime based on progressive delay
    setStorageData({
      lastShown: new Date(now).toISOString(),
      nextShowTime,
      showCount: currentShowCount + 1,
    })

    // Make visible immediately
    setIsVisible(true)

    // Start animation after a frame for smooth CSS transition
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        setIsAnimating(true)
      })
    })
  }, [])

  useEffect(() => {
    clearScheduledTimeouts()

    // Don't show popup if user is not authenticated
    if (!getAuthToken()) {
      hasShownRef.current = false
      setIsVisible(false)
      setIsAnimating(false)
      return
    }

    const checkShouldShow = () => {
      const data = getStorageData()
      const now = Date.now()

      if (!data) {
        // First time - schedule for initial delay and store it with showCount 0
        const nextShowTime = new Date(now + FIRST_SHOW_DELAY).toISOString()
        setStorageData({ lastShown: null, nextShowTime, showCount: 0 })
        schedulePopup(FIRST_SHOW_DELAY, showPopup)
        return
      }

      // Check if it's time to show based on stored nextShowTime
      const nextShowTimestamp = new Date(data.nextShowTime).getTime()
      const timeUntilShow = nextShowTimestamp - now

      if (timeUntilShow <= 0) {
        // Time has passed, show now so refresh cannot retrigger in a delay window
        showPopup()
      } else {
        // Schedule for the remaining time
        schedulePopup(timeUntilShow, showPopup)
      }
    }

    checkShouldShow()

    return () => {
      clearScheduledTimeouts()
    }
  }, [clearScheduledTimeouts, schedulePopup, showPopup])

  // Don't render popup if user is not authenticated
  if (!getAuthToken()) {
    return null
  }

  const handleClose = () => {
    setIsAnimating(false)
    setTimeout(() => setIsVisible(false), 280)
  }

  const handleDonate = () => {
    window.open(DONATION_URL, '_blank', 'noopener,noreferrer')
    handleClose()
  }

  const handleGitHub = () => {
    window.open(REPO_URL, '_blank', 'noopener,noreferrer')
    handleClose()
  }

  if (!isVisible) return null

  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-0 z-[100] flex justify-center p-3 sm:p-5 md:justify-end md:p-6">
      {/* Soft vignette — no heavy modal blur */}
      <div
        className={cn(
          'pointer-events-auto absolute inset-0 bg-gradient-to-t from-black/50 via-black/10 to-transparent',
          'transition-opacity duration-300 ease-[cubic-bezier(0.22,1,0.36,1)]',
          isAnimating ? 'opacity-100' : 'opacity-0',
        )}
        onClick={handleClose}
        aria-hidden
      />

      <aside
        role="dialog"
        aria-labelledby="donation-sheet-title"
        aria-modal="true"
        className={cn(
          'pointer-events-auto relative w-full max-w-[22rem] overflow-hidden rounded-2xl border border-white/10',
          'bg-[#0c1118]/95 text-white shadow-[0_24px_80px_-24px_rgba(0,0,0,0.75)] backdrop-blur-xl',
          'transition-[transform,opacity] duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] will-change-transform',
          isAnimating ? 'translate-y-0 opacity-100' : 'translate-y-6 opacity-0',
        )}
      >
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-sky-400/50 to-transparent" />
        <div className="absolute -start-16 -top-20 size-40 rounded-full bg-sky-500/10 blur-3xl" aria-hidden />

        <button
          type="button"
          onClick={handleClose}
          className="absolute end-2.5 top-2.5 z-10 rounded-lg p-1.5 text-white/45 transition-colors hover:bg-white/5 hover:text-white"
          aria-label={t('close', { defaultValue: 'Close' })}
        >
          <X className="size-3.5" />
        </button>

        <div className="relative space-y-4 p-4 pt-5 sm:p-5">
          <div className="flex items-start gap-3 pe-6">
            <div className="flex size-9 shrink-0 items-center justify-center rounded-xl border border-sky-400/20 bg-sky-400/10 text-sky-300">
              <Sparkles className="size-4" />
            </div>
            <div className="min-w-0 space-y-1">
              <p className="font-mono text-[10px] font-semibold tracking-[0.16em] text-sky-300/80 uppercase">
                {t('donation.eyebrow', { defaultValue: 'Keep the uplink alive' })}
              </p>
              <h3 id="donation-sheet-title" className="text-[15px] leading-snug font-semibold tracking-tight">
                {t('donation.title', { defaultValue: 'Support HPXPANEL' })}
              </h3>
              <p className="text-[12px] leading-relaxed text-white/55">
                {t('donation.message', {
                  defaultValue: 'Fuel the next features — donate or star the repo if HPXPANEL helps your stack.',
                })}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={handleDonate}
              className={cn(
                'group flex h-10 items-center justify-center gap-1.5 rounded-xl bg-sky-400 px-3',
                'text-[12px] font-semibold text-[#071018] transition-[transform,background-color] duration-150',
                'hover:bg-sky-300 active:scale-[0.98]',
              )}
            >
              {t('donation.donate', { defaultValue: 'Donate' })}
              <ArrowUpRight className="size-3.5 opacity-70 transition-transform duration-150 group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
            </button>
            <button
              type="button"
              onClick={handleGitHub}
              className={cn(
                'group flex h-10 items-center justify-center gap-1.5 rounded-xl border border-white/12 bg-white/[0.04] px-3',
                'text-[12px] font-medium text-white/85 transition-[transform,background-color,border-color] duration-150',
                'hover:border-white/20 hover:bg-white/[0.07] active:scale-[0.98]',
              )}
            >
              <Github className="size-3.5" />
              {t('donation.starOnGitHub', { defaultValue: 'Star' })}
            </button>
          </div>

          <button
            type="button"
            onClick={handleClose}
            className="w-full text-center text-[11px] text-white/35 transition-colors hover:text-white/60"
          >
            {t('donation.later', { defaultValue: 'Not now' })}
          </button>
        </div>
      </aside>
    </div>
  )
}
