import { cn } from '@/lib/utils'
import type { SubThemeMode } from '@/service/api'
import { Moon, Sun } from 'lucide-react'
import { useTranslation } from 'react-i18next'

interface ModeControlCardProps {
  mode: SubThemeMode
  disabled?: boolean
  onChange: (mode: SubThemeMode) => void
}

const OPTIONS: { value: SubThemeMode; icon: typeof Sun }[] = [
  { value: 'dark', icon: Moon },
  { value: 'light', icon: Sun },
]

export function ModeControlCard({ mode, disabled, onChange }: ModeControlCardProps) {
  const { t } = useTranslation()

  return (
    <div className="border-border bg-card flex flex-col justify-between gap-5 border-2 border-dashed p-5">
      <div className="space-y-1.5">
        <span className="text-primary font-mono text-[10px] font-bold tracking-[0.16em] uppercase">{t('subTheme.mode.kicker')}</span>
        <h3 className="font-display text-lg font-bold tracking-tight">{t('subTheme.mode.title')}</h3>
        <p className="text-muted-foreground text-xs leading-relaxed">{t('subTheme.mode.description')}</p>
      </div>
      <div role="radiogroup" aria-label={t('subTheme.mode.title')} className="grid grid-cols-2 gap-2">
        {OPTIONS.map(({ value, icon: Icon }) => {
          const active = mode === value
          return (
            <button
              key={value}
              type="button"
              role="radio"
              aria-checked={active}
              disabled={disabled}
              onClick={() => onChange(value)}
              className={cn(
                'flex items-center justify-center gap-2 border-2 px-3 py-3 text-sm font-semibold transition-colors',
                'focus-visible:ring-ring focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none disabled:opacity-60',
                active ? 'border-primary bg-primary text-primary-foreground' : 'border-border bg-muted/40 hover:border-primary/60',
              )}
            >
              <Icon className="size-4" aria-hidden="true" />
              {t(`subTheme.mode.${value}`)}
            </button>
          )
        })}
      </div>
    </div>
  )
}
