import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { SubTheme, SubThemeMode } from '@/service/api'
import { Check } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { st, themeText } from '../lib/i18n'
import { ThemeMock } from './theme-mock'

const FONT_PAIRS: Record<SubTheme, string> = {
  terminal: 'Chakra Petch · JetBrains Mono',
  aurora: 'Playfair Display · DM Sans',
  nova: 'Syne · Manrope',
  atlas: 'Outfit · Source Sans 3',
  pulse: 'Space Grotesk · IBM Plex Sans',
}

interface ThemeCardProps {
  theme: SubTheme
  mode: SubThemeMode
  selected: boolean
  live: boolean
  disabled?: boolean
  onSelect: (theme: SubTheme) => void
}

export function ThemeCard({ theme, mode, selected, live, disabled, onSelect }: ThemeCardProps) {
  const { t } = useTranslation()

  return (
    <button
      type="button"
      role="radio"
      aria-checked={selected}
      disabled={disabled}
      onClick={() => onSelect(theme)}
      className={cn(
        'group border-border bg-card relative flex flex-col overflow-hidden border-2 text-start transition-all duration-200',
        'focus-visible:ring-ring focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none',
        'hover:-translate-y-0.5 hover:shadow-lg disabled:cursor-not-allowed disabled:opacity-60',
        selected ? 'border-primary ring-primary/40 shadow-lg ring-2' : 'hover:border-primary/60',
      )}
    >
      <div className="relative border-b">
        <ThemeMock theme={theme} mode={mode} />
        <div className="absolute end-2 top-2 flex items-center gap-1.5">
          {live && (
            <Badge variant="green" className="shadow-none normal-case">
              {st(t, 'subTheme.live', 'Live')}
            </Badge>
          )}
          {selected && (
            <span className="bg-primary text-primary-foreground grid size-6 place-items-center shadow-md" aria-hidden="true">
              <Check className="size-4" />
            </span>
          )}
        </div>
      </div>
      <div className="flex flex-1 flex-col gap-1.5 p-4">
        <div className="flex items-center justify-between gap-2">
          <h3 className="font-display text-base font-bold tracking-tight">{themeText(t, theme, 'name')}</h3>
          <span className="text-muted-foreground font-mono text-[10px] tracking-wider uppercase">{themeText(t, theme, 'tag')}</span>
        </div>
        <p className="text-muted-foreground text-xs leading-relaxed">{themeText(t, theme, 'description')}</p>
        <p className="text-muted-foreground/80 mt-auto pt-2 font-mono text-[10px]" dir="ltr">
          {FONT_PAIRS[theme]}
        </p>
      </div>
    </button>
  )
}
