import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import useDirDetection from '@/hooks/use-dir-detection'
import { getDocsUrl } from '@/utils/docs-url'
import { cn } from '@/lib/utils'
import { HelpCircle, LucideIcon, Plus } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useLocation } from 'react-router'

interface PageHeaderProps {
  title: string
  description?: string
  index?: string
  sectorLabel?: string
  buttonText?: string
  onButtonClick?: () => void
  buttonIcon?: LucideIcon
  buttonTooltip?: string
  tutorialUrl?: string
  className?: string
}

export default function PageHeader({
  title,
  description,
  index = '01',
  sectorLabel = 'Mission brief',
  buttonText,
  onButtonClick,
  buttonIcon: Icon = Plus,
  buttonTooltip,
  tutorialUrl,
  className,
}: PageHeaderProps) {
  const { t } = useTranslation()
  const dir = useDirDetection()
  const location = useLocation()

  const docsUrl = tutorialUrl || getDocsUrl(location.pathname)

  return (
    <div dir={dir} className={cn('mission-brief relative mx-auto flex w-full flex-row items-center justify-between gap-4 overflow-hidden px-4 py-5 md:px-6 md:py-7', className)}>
      <div className="mission-brief__index" aria-hidden="true">
        {index}
      </div>
      <div className="border-primary relative z-10 flex min-w-0 flex-1 flex-col gap-y-1.5 border-s-2 ps-4">
        <span className="text-primary font-mono text-[10px] font-bold tracking-[0.16em] uppercase">{sectorLabel}</span>
        <div className="flex min-w-0 items-center gap-2.5">
          <h1 className="font-display truncate text-2xl font-bold tracking-tight sm:text-3xl">{t(title)}</h1>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <a
                  href={docsUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-muted-foreground hover:border-primary hover:bg-primary/10 hover:text-primary focus-visible:ring-ring inline-flex h-8 w-8 items-center justify-center border border-transparent transition-colors focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none"
                  aria-label={t('tutorial', { defaultValue: 'View tutorial' })}
                >
                  <HelpCircle className="h-4 w-4" />
                </a>
              </TooltipTrigger>
              <TooltipContent>
                <p>{t('tutorial', { defaultValue: 'View tutorial' })}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
        {description && <span className="text-muted-foreground max-w-2xl text-xs leading-relaxed sm:text-sm">{t(description)}</span>}
      </div>
      {buttonText && onButtonClick && (
        <div className="relative z-10 shrink-0">
          {buttonTooltip ? (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button className="flex items-center" onClick={onButtonClick} size="sm">
                    {Icon && <Icon />}
                    <span>{t(buttonText)}</span>
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  <p>{buttonTooltip}</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          ) : (
            <Button className="flex items-center" onClick={onButtonClick} size="sm">
              {Icon && <Icon />}
              <span>{t(buttonText)}</span>
            </Button>
          )}
        </div>
      )}
    </div>
  )
}
