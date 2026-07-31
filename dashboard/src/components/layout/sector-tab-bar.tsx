import { cn } from '@/lib/utils'
import type { LucideIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'

export type SectorTab = {
  id: string
  label: string
  icon: LucideIcon
  url: string
  mobileLabel?: string
}

type SectorTabBarProps = {
  tabs: SectorTab[]
  activeId: string
  sector: string
  index?: string
  onSelect?: (tab: SectorTab) => void
  className?: string
}

export function SectorTabBar({ tabs, activeId, sector, index = '01', onSelect, className }: SectorTabBarProps) {
  const { t } = useTranslation()

  return (
    <nav
      className={cn('bg-card text-foreground relative flex min-w-0 items-stretch overflow-hidden border-y-2 border-[hsl(var(--pixel-border))]', className)}
      aria-label={`${sector} sector navigation`}
    >
      <div className="bg-foreground text-background relative hidden w-36 shrink-0 flex-col justify-between overflow-hidden px-4 py-3 sm:flex lg:w-44">
        <span className="font-mono text-[10px] font-bold tracking-[0.18em] uppercase opacity-65">HPXPANEL // {index}</span>
        <span className="font-display mt-2 text-sm leading-none font-black tracking-[0.08em] uppercase">{sector}</span>
        <span className="bg-primary absolute end-0 top-0 h-full w-1" aria-hidden="true" />
      </div>

      <div className="scrollbar-hide flex min-w-0 flex-1 snap-x snap-mandatory overflow-x-auto overscroll-x-contain">
        {tabs.map((tab, tabIndex) => {
          const Icon = tab.icon
          const isActive = activeId === tab.id
          const label = t(tab.label)
          const content = (
            <>
              <span className={cn('absolute end-2 top-2 font-mono text-[9px] font-bold tabular-nums', isActive ? 'text-primary-foreground/65' : 'text-muted-foreground/55')} aria-hidden="true">
                {String(tabIndex + 1).padStart(2, '0')}
              </span>
              <Icon className="h-[18px] w-[18px] shrink-0" aria-hidden="true" />
              <span className={cn('truncate', tab.mobileLabel && 'hidden sm:inline')}>{label}</span>
              {tab.mobileLabel && <span className="truncate sm:hidden">{t(tab.mobileLabel)}</span>}
              <span
                className={cn('absolute inset-x-0 bottom-0 h-1 transition-colors motion-reduce:transition-none', isActive ? 'bg-primary-foreground' : 'group-hover:bg-primary/45 bg-transparent')}
                aria-hidden="true"
              />
            </>
          )
          const itemClassName = cn(
            'group relative flex min-h-14 min-w-[9.5rem] snap-start items-center gap-2 border-e border-[hsl(var(--pixel-border)/0.45)] px-4 pt-3 pb-2 pe-8 text-start font-mono text-xs font-bold tracking-[0.04em] uppercase outline-none transition-colors motion-reduce:transition-none sm:min-w-[10.5rem]',
            'focus-visible:z-10 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset',
            isActive ? 'bg-primary text-primary-foreground' : 'bg-card text-muted-foreground hover:bg-accent hover:text-accent-foreground',
          )

          if (!onSelect) {
            return (
              <div key={tab.id} className={itemClassName} aria-current={isActive ? 'page' : undefined}>
                {content}
              </div>
            )
          }

          return (
            <button key={tab.id} type="button" onClick={() => onSelect(tab)} className={cn(itemClassName, 'cursor-pointer')} aria-current={isActive ? 'page' : undefined} aria-label={label}>
              {content}
            </button>
          )
        })}
      </div>

      <div className="bg-muted/60 hidden w-8 shrink-0 items-center justify-center border-s border-[hsl(var(--pixel-border)/0.45)] xl:flex" aria-hidden="true">
        <span className="text-muted-foreground -rotate-90 font-mono text-[9px] font-bold tracking-[0.2em] whitespace-nowrap uppercase">Sector online</span>
      </div>
    </nav>
  )
}
