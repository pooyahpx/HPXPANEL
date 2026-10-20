import { Theme, useTheme } from '@/app/providers/theme-provider'
import { Button } from '@/components/ui/button'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { SidebarContext } from '@/components/ui/sidebar'
import { Monitor, Moon, Sun } from 'lucide-react'
import { useCallback, useContext } from 'react'
import { useTranslation } from 'react-i18next'

type ThemeToggleProps = {
  variant?: 'default' | 'header'
}

export function ThemeToggle({ variant = 'default' }: ThemeToggleProps) {
  const { setTheme } = useTheme()
  const { t } = useTranslation()

  const sidebarContext = useContext(SidebarContext)
  const sidebarState: 'expanded' | 'collapsed' = sidebarContext?.state ?? 'expanded'
  const isMobile = sidebarContext?.isMobile ?? false

  const toggleTheme = useCallback(
    (theme: Theme) => {
      setTheme(theme)
    },
    [setTheme],
  )

  const trigger = (
    <Button
      variant="outline"
      size={variant === 'header' ? 'sm' : 'icon'}
      className={
        variant === 'header'
          ? 'border-border/70 bg-card/40 hover:bg-accent/60 h-8 w-8 cursor-pointer px-0'
          : 'cursor-pointer transition-colors duration-200'
      }
    >
      <Sun className="h-3.5 w-3.5 transition-all duration-300 ease-in-out dark:hidden" />
      <Moon className="hidden h-3.5 w-3.5 transition-all duration-300 ease-in-out dark:block" />
      <span className="sr-only">{t('theme.toggle')}</span>
    </Button>
  )

  if (variant === 'header') {
    return (
      <DropdownMenu>
        <DropdownMenuTrigger asChild>{trigger}</DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="min-w-[9rem]">
          <DropdownMenuItem onClick={() => toggleTheme('light')} className="cursor-pointer">
            <Sun className="mr-2 h-4 w-4" />
            {t('theme.light')}
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => toggleTheme('dark')} className="cursor-pointer">
            <Moon className="mr-2 h-4 w-4" />
            {t('theme.dark')}
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => toggleTheme('system')} className="cursor-pointer">
            <Monitor className="mr-2 h-4 w-4" />
            {t('theme.system')}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    )
  }

  if (sidebarState === 'collapsed' && !isMobile) {
    return (
      <Popover>
        <PopoverTrigger asChild>
          <Button variant="outline" size="icon" className="h-8 w-8 cursor-pointer transition-colors duration-200">
            <Sun className="transition-all duration-300 ease-in-out dark:hidden" />
            <Moon className="hidden transition-all duration-300 ease-in-out dark:block" />
            <span className="sr-only">{t('theme.toggle')}</span>
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-48 p-2" side="right" align="start">
          <div className="space-y-1">
            <div className="px-2 py-1.5 text-sm font-semibold">{t('theme.title', { defaultValue: 'Theme' })}</div>
            <Button variant="ghost" size="sm" className="w-full cursor-pointer justify-start" onClick={() => toggleTheme('light')}>
              <Sun className="mr-2 h-4 w-4" />
              {t('theme.light')}
            </Button>
            <Button variant="ghost" size="sm" className="w-full cursor-pointer justify-start" onClick={() => toggleTheme('dark')}>
              <Moon className="mr-2 h-4 w-4" />
              {t('theme.dark')}
            </Button>
            <Button variant="ghost" size="sm" className="w-full cursor-pointer justify-start" onClick={() => toggleTheme('system')}>
              <Monitor className="mr-2 h-4 w-4" />
              {t('theme.system')}
            </Button>
          </div>
        </PopoverContent>
      </Popover>
    )
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>{trigger}</DropdownMenuTrigger>
      <DropdownMenuContent align="start" side="top" className="transition-all duration-200 ease-in-out">
        <DropdownMenuItem onClick={() => toggleTheme('light')} className="hover:bg-accent cursor-pointer transition-colors duration-150">
          <Sun className="mr-2 h-4 w-4 transition-transform duration-200 hover:scale-110" />
          {t('theme.light')}
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => toggleTheme('dark')} className="hover:bg-accent cursor-pointer transition-colors duration-150">
          <Moon className="mr-2 h-4 w-4 transition-transform duration-200 hover:scale-110" />
          {t('theme.dark')}
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => toggleTheme('system')} className="hover:bg-accent cursor-pointer transition-colors duration-150">
          <Monitor className="mr-2 h-4 w-4 transition-transform duration-200 hover:scale-110" />
          {t('theme.system')}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
