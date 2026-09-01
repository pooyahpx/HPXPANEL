import { ArrowRight, Copy, ExternalLink, Rocket, Sparkles, Terminal, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useVersionCheck } from '@/hooks/use-version-check'
import useDirDetection from '@/hooks/use-dir-detection'
import { useClipboard } from '@/hooks/use-clipboard'
import { toast } from 'sonner'
import { useSystemVersion } from '@/hooks/use-system-version'
import { useAdmin } from '@/hooks/use-admin'
import { isOwner } from '@/utils/rbac'

const VERSION_BANNER_STORAGE_KEY = 'version_update_banner_closed'
const HOURS_TO_HIDE = 24
const UPDATE_COMMAND = 'hpxpanel update'

interface BannerStorage {
  timestamp: number
  version: string
}

export function VersionUpdateBanner() {
  const { t } = useTranslation()
  const isRTL = useDirDetection() === 'rtl'
  const { copy } = useClipboard()
  const { admin } = useAdmin()
  const isOwnerAdmin = isOwner(admin)
  const { currentVersion } = useSystemVersion({ enabled: isOwnerAdmin })
  const [isVisible, setIsVisible] = useState(false)
  const [isClosing, setIsClosing] = useState(false)
  const [isAnimating, setIsAnimating] = useState(false)
  const { hasUpdate, latestVersion, releaseUrl, isLoading } = useVersionCheck(currentVersion, { enabled: isOwnerAdmin })

  useEffect(() => {
    if (!isOwnerAdmin || isLoading || !hasUpdate || !currentVersion) {
      setIsVisible(false)
      setIsAnimating(false)
      return
    }

    const checkShouldShow = () => {
      try {
        const stored = localStorage.getItem(VERSION_BANNER_STORAGE_KEY)
        let bannerData: BannerStorage | null = null

        if (stored) {
          bannerData = JSON.parse(stored)
        }

        if (bannerData && bannerData.version !== latestVersion) {
          setIsVisible(true)
          setTimeout(() => setIsAnimating(true), 80)
          return
        }

        if (!bannerData) {
          setIsVisible(true)
          setTimeout(() => setIsAnimating(true), 80)
          return
        }

        const now = Date.now()
        const hoursSinceClose = (now - bannerData.timestamp) / (1000 * 60 * 60)

        if (hoursSinceClose >= HOURS_TO_HIDE) {
          setIsVisible(true)
          setTimeout(() => setIsAnimating(true), 80)
        }
      } catch {
        setIsVisible(true)
        setTimeout(() => setIsAnimating(true), 80)
      }
    }

    checkShouldShow()
  }, [hasUpdate, isOwnerAdmin, latestVersion, currentVersion, isLoading])

  const handleClose = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsClosing(true)

    if (latestVersion) {
      const bannerData: BannerStorage = {
        timestamp: Date.now(),
        version: latestVersion,
      }
      localStorage.setItem(VERSION_BANNER_STORAGE_KEY, JSON.stringify(bannerData))
    }

    setTimeout(() => setIsVisible(false), 320)
  }

  const handleCopyCommand = async (e?: React.MouseEvent) => {
    e?.preventDefault()
    e?.stopPropagation()
    await copy(UPDATE_COMMAND)
    toast.success(t('version.commandCopied'))
  }

  if (!isOwnerAdmin || isLoading || !hasUpdate || !isVisible || !latestVersion || !currentVersion) return null

  const releaseLink = releaseUrl || 'https://github.com/pooyahpx/HPXPANEL/releases'

  return (
    <div
      className={cn(
        'update-toast fixed bottom-3 z-[60] sm:bottom-5',
        isRTL ? 'right-2 left-2 sm:right-auto sm:left-5' : 'right-2 left-2 sm:right-5 sm:left-auto',
        isClosing ? 'update-toast--closing' : isAnimating ? 'update-toast--visible' : 'update-toast--hidden',
      )}
      dir={isRTL ? 'rtl' : 'ltr'}
      role="status"
      aria-live="polite"
    >
      <div className="update-toast__glow" aria-hidden="true" />
      <div className="update-toast__card">
        <div className="update-toast__scan" aria-hidden="true" />

        <Button
          variant="ghost"
          size="icon"
          onClick={handleClose}
          className={cn(
            'update-toast__close text-muted-foreground hover:text-foreground absolute top-2 z-20 h-8 w-8 rounded-md',
            isRTL ? 'left-2' : 'right-2',
          )}
          aria-label={t('version.closeBanner')}
        >
          <X className="h-4 w-4" />
        </Button>

        <div className="update-toast__header">
          <div className="update-toast__icon-wrap">
            <Rocket className="h-5 w-5" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="update-toast__badge">
                <Sparkles className="h-3 w-3" />
                {t('version.updateReady')}
              </span>
              <span className="text-muted-foreground font-mono text-[10px] tracking-[0.14em] uppercase">
                HPX // uplink
              </span>
            </div>
            <h3 className="text-foreground mt-1 text-base leading-tight font-bold tracking-tight sm:text-lg">
              {t('version.newVersionAvailable')}
            </h3>
            <p className="text-muted-foreground mt-1 text-xs leading-relaxed sm:text-sm">{t('version.clickToUpdate')}</p>
          </div>
        </div>

        <div className="update-toast__versions">
          <div className="update-toast__version-pill update-toast__version-pill--current">
            <span className="text-muted-foreground text-[10px] font-semibold tracking-wide uppercase">
              {t('version.currentVersion')}
            </span>
            <span className="font-mono text-sm font-bold">v{currentVersion}</span>
          </div>

          <div className="update-toast__arrow" aria-hidden="true">
            <ArrowRight className={cn('h-4 w-4', isRTL && 'rotate-180')} />
          </div>

          <div className="update-toast__version-pill update-toast__version-pill--latest">
            <span className="text-[10px] font-semibold tracking-wide uppercase text-emerald-300/90">
              {t('version.latestVersion')}
            </span>
            <span className="font-mono text-sm font-bold text-emerald-300">v{latestVersion}</span>
          </div>
        </div>

        <div className="update-toast__terminal">
          <div className="flex items-center gap-2 border-b border-white/10 px-3 py-2">
            <Terminal className="text-primary h-3.5 w-3.5" />
            <span className="text-muted-foreground font-mono text-[10px] tracking-wide uppercase">
              {t('version.updateCommandLabel')}
            </span>
          </div>
          <button
            type="button"
            onClick={handleCopyCommand}
            className="group flex w-full items-center justify-between gap-3 px-3 py-3 text-start transition-colors hover:bg-white/5"
            title={t('copy')}
          >
            <code className="text-foreground font-mono text-sm font-semibold">{UPDATE_COMMAND}</code>
            <span className="text-primary flex shrink-0 items-center gap-1 rounded-md border border-primary/30 bg-primary/10 px-2 py-1 text-[10px] font-bold tracking-wide uppercase transition group-hover:bg-primary/20">
              <Copy className="h-3 w-3" />
              {t('copy')}
            </span>
          </button>
        </div>

        <div className="update-toast__actions">
          <Button type="button" className="update-toast__btn-primary flex-1 gap-2" onClick={handleCopyCommand}>
            <Copy className="h-4 w-4" />
            {t('version.copyUpdateCommand')}
          </Button>
          <Button type="button" variant="outline" className="update-toast__btn-secondary flex-1 gap-2" asChild>
            <a href={releaseLink} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="h-4 w-4" />
              {t('version.viewRelease')}
            </a>
          </Button>
        </div>
      </div>
    </div>
  )
}
