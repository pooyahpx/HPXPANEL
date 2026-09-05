import { cn } from '@/lib/utils'
import { useCoreEditorStore } from '@/features/core-editor/state/core-editor-store'
import { IPSEC_CORE_SECTION_NAV, WG_CORE_SECTION_NAV, XRAY_CORE_SECTION_NAV } from '@/features/core-editor/kit/core-section-nav'
import { useTranslation } from 'react-i18next'

/** Horizontal section tabs — Command Deck sector strip (matches Nodes sector nav). */
export function CoreSectionTabs({ className }: { className?: string }) {
  const { t } = useTranslation()
  const kind = useCoreEditorStore(s => s.kind)
  const active = useCoreEditorStore(s => s.activeSection)
  const setActive = useCoreEditorStore(s => s.setActiveSection)
  const items = kind === 'wg' ? WG_CORE_SECTION_NAV : kind === 'ikev2' || kind === 'l2tp' || kind === 'openvpn' ? IPSEC_CORE_SECTION_NAV : XRAY_CORE_SECTION_NAV

  return (
    <nav
      className={cn('bg-card text-foreground relative flex min-w-0 items-stretch overflow-hidden border-y-2 border-[hsl(var(--pixel-border))]', className)}
      role="tablist"
      aria-label={t('coreEditor.section.label', { defaultValue: 'Section' })}
    >
      <div className="bg-foreground text-background relative hidden w-36 shrink-0 flex-col justify-between overflow-hidden px-4 py-3 sm:flex lg:w-40">
        <span className="font-mono text-[10px] font-bold tracking-[0.18em] uppercase opacity-65">HPXPANEL // 03</span>
        <span className="font-display mt-2 text-sm leading-none font-black tracking-[0.08em] uppercase">Core deck</span>
        <span className="bg-primary absolute end-0 top-0 h-full w-1" aria-hidden="true" />
      </div>

      <div className="scrollbar-hide flex min-w-0 flex-1 snap-x snap-mandatory overflow-x-auto overscroll-x-contain">
        {items.map((item, tabIndex) => {
          const Icon = item.icon
          const isActive = active === item.id
          const label = t(item.labelKey, { defaultValue: item.defaultLabel })
          return (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={isActive}
              aria-label={label}
              onClick={() => setActive(item.id)}
              className={cn(
                'group relative flex min-h-14 min-w-[8.5rem] snap-start items-center gap-2 border-e border-[hsl(var(--pixel-border)/0.45)] px-4 pt-3 pb-2 pe-8 text-start font-mono text-xs font-bold tracking-[0.04em] uppercase outline-none transition-colors sm:min-w-[9.5rem]',
                'focus-visible:z-10 focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset',
                isActive ? 'bg-primary text-primary-foreground' : 'bg-card text-muted-foreground hover:bg-accent hover:text-accent-foreground',
              )}
            >
              <span className={cn('absolute end-2 top-2 font-mono text-[9px] font-bold tabular-nums', isActive ? 'text-primary-foreground/65' : 'text-muted-foreground/55')} aria-hidden="true">
                {String(tabIndex + 1).padStart(2, '0')}
              </span>
              <Icon className="h-[18px] w-[18px] shrink-0" aria-hidden="true" />
              <span className="truncate">{label}</span>
              <span
                className={cn('absolute inset-x-0 bottom-0 h-1 transition-colors', isActive ? 'bg-primary-foreground' : 'group-hover:bg-primary/45 bg-transparent')}
                aria-hidden="true"
              />
            </button>
          )
        })}
      </div>

      <div className="bg-muted/60 hidden w-8 shrink-0 items-center justify-center border-s border-[hsl(var(--pixel-border)/0.45)] xl:flex" aria-hidden="true">
        <span className="text-muted-foreground -rotate-90 font-mono text-[9px] font-bold tracking-[0.2em] whitespace-nowrap uppercase">Live config</span>
      </div>
    </nav>
  )
}

/** Non-interactive tab strip matching {@link CoreSectionTabs} (loading / skeleton shell). */
export function CoreSectionTabsPlaceholder({
  kind,
  activeSectionId,
  className,
}: {
  kind: 'xray' | 'wg'
  /** Defaults: inbounds (xray) / interface (wg). */
  activeSectionId?: string
  className?: string
}) {
  const { t } = useTranslation()
  const items = kind === 'wg' ? WG_CORE_SECTION_NAV : XRAY_CORE_SECTION_NAV
  const active = activeSectionId ?? (kind === 'wg' ? 'interface' : 'inbounds')

  return (
    <nav className={cn('bg-card relative flex min-w-0 items-stretch overflow-hidden border-y-2 border-[hsl(var(--pixel-border))]', className)} role="presentation" aria-busy="true">
      <div className="bg-foreground text-background relative hidden w-36 shrink-0 flex-col justify-between overflow-hidden px-4 py-3 sm:flex lg:w-40">
        <span className="font-mono text-[10px] font-bold tracking-[0.18em] uppercase opacity-65">HPXPANEL // 03</span>
        <span className="font-display mt-2 text-sm leading-none font-black tracking-[0.08em] uppercase">Core deck</span>
        <span className="bg-primary absolute end-0 top-0 h-full w-1" aria-hidden="true" />
      </div>
      <div className="scrollbar-hide flex min-w-0 flex-1 overflow-x-auto">
        {items.map((item, tabIndex) => {
          const Icon = item.icon
          const isActive = active === item.id
          return (
            <div
              key={item.id}
              className={cn(
                'relative flex min-h-14 min-w-[8.5rem] items-center gap-2 border-e border-[hsl(var(--pixel-border)/0.45)] px-4 pt-3 pb-2 pe-8 font-mono text-xs font-bold tracking-[0.04em] uppercase sm:min-w-[9.5rem]',
                isActive ? 'bg-primary text-primary-foreground' : 'text-muted-foreground',
              )}
            >
              <span className={cn('absolute end-2 top-2 font-mono text-[9px] font-bold tabular-nums', isActive ? 'text-primary-foreground/65' : 'text-muted-foreground/55')} aria-hidden="true">
                {String(tabIndex + 1).padStart(2, '0')}
              </span>
              <Icon className="h-[18px] w-[18px] shrink-0" aria-hidden />
              <span className="truncate">{t(item.labelKey, { defaultValue: item.defaultLabel })}</span>
            </div>
          )
        })}
      </div>
    </nav>
  )
}
