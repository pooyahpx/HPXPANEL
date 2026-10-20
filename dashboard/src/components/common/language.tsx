import { Button } from '@/components/ui/button'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { SidebarContext } from '@/components/ui/sidebar'
import { cn } from '@/lib/utils'
import { LanguagesIcon } from 'lucide-react'
import { useContext } from 'react'
import { useTranslation } from 'react-i18next'

/** Languages with complete locale files (ru/zh may still have English fallbacks in newly filled namespaces). */
export const LANGUAGE_PICKER_OPTIONS = [
  { code: 'en', label: 'English' },
  { code: 'fa', label: 'فارسی' },
  { code: 'zh', label: '简体中文' },
  { code: 'ru', label: 'Русский' },
] as const

type LanguageProps = {
  /** Compact top-bar control showing current code (EN / FA) like Nexora. */
  variant?: 'default' | 'header'
}

export const Language: React.FC<LanguageProps> = ({ variant = 'default' }) => {
  const { i18n, t } = useTranslation()

  const sidebarContext = useContext(SidebarContext)
  const sidebarState: 'expanded' | 'collapsed' = sidebarContext?.state ?? 'expanded'
  const isMobile = sidebarContext?.isMobile ?? false

  const changeLanguage = async (lang: string) => {
    await i18n.changeLanguage(lang)
    document.documentElement.lang = lang
    document.documentElement.setAttribute('dir', i18n.dir())
  }

  const code = (i18n.language || 'en').slice(0, 2).toUpperCase()

  if (variant === 'header') {
    return (
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="outline"
            size="sm"
            className="border-border/70 bg-card/50 hover:bg-accent/70 h-8 cursor-pointer gap-1.5 px-2.5 text-[11px] font-semibold tracking-wide"
          >
            <LanguagesIcon className="h-3.5 w-3.5 opacity-80" />
            <span>{code}</span>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="min-w-[9rem]">
          {LANGUAGE_PICKER_OPTIONS.map(({ code: c, label }) => (
            <DropdownMenuItem
              key={c}
              onClick={() => changeLanguage(c)}
              className={cn('cursor-pointer', c === i18n.language.slice(0, 2) && 'bg-accent')}
            >
              {label}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
    )
  }

  if (sidebarState === 'collapsed' && !isMobile) {
    return (
      <Popover>
        <PopoverTrigger asChild>
          <Button variant="outline" size="icon" className="h-8 w-8 cursor-pointer">
            <LanguagesIcon className="h-4 w-4" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-48 p-2" side="right" align="start">
          <div className="space-y-1">
            <div className="px-2 py-1.5 text-sm font-semibold">{t('language.title', { defaultValue: 'Language' })}</div>
            {LANGUAGE_PICKER_OPTIONS.map(({ code: c, label }) => (
              <Button key={c} variant="ghost" size="sm" className="w-full cursor-pointer justify-start" onClick={() => changeLanguage(c)}>
                {label}
              </Button>
            ))}
          </div>
        </PopoverContent>
      </Popover>
    )
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="icon" className="cursor-pointer">
          <LanguagesIcon className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" side="top">
        {LANGUAGE_PICKER_OPTIONS.map(({ code: c, label }) => (
          <DropdownMenuItem key={c} onClick={() => changeLanguage(c)} className="cursor-pointer">
            {label}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
