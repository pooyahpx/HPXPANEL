import { AnimatePresence, motion } from 'framer-motion'
import type { LucideIcon } from 'lucide-react'
import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { NavLink, useLocation, useNavigate } from 'react-router'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'

export type DualTierSubItem = {
  title: string
  url: string
  icon: LucideIcon
  matchPrefix?: boolean
  badge?: number | string
  target?: string
}

export type DualTierNavItem = {
  title: string
  url: string
  icon: LucideIcon
  badge?: number | string
  items?: DualTierSubItem[]
  target?: string
}

type SidebarDualTierProps = {
  items: DualTierNavItem[]
  footerItems?: DualTierNavItem[]
  header?: ReactNode
  footer?: ReactNode
  featureCard?: ReactNode
  side?: 'left' | 'right'
  className?: string
  onNavigate?: () => void
}

function isItemActive(pathname: string, item: DualTierNavItem | DualTierSubItem, matchPrefix?: boolean) {
  if (item.url.startsWith('http')) return false
  if (item.url === '/') return pathname === '/'
  const prefix = matchPrefix ?? ('matchPrefix' in item ? item.matchPrefix : pathname.startsWith(item.url))
  if (prefix) return pathname === item.url || pathname.startsWith(`${item.url}/`)
  return pathname === item.url
}

function findActiveSection(pathname: string, items: DualTierNavItem[]) {
  const withChildren = items.find(item => item.items?.some(sub => isItemActive(pathname, sub, sub.matchPrefix ?? true)))
  if (withChildren) return withChildren.title
  const direct = items.find(item => isItemActive(pathname, item, !!item.items?.length))
  return direct?.title ?? items.find(item => item.items?.length)?.title ?? null
}

export function SidebarDualTier({ items, footerItems = [], header, footer, featureCard, side = 'left', className, onNavigate }: SidebarDualTierProps) {
  const { t } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()
  const [activeSection, setActiveSection] = useState<string | null>(() => findActiveSection(location.pathname, items))
  const [panelOpen, setPanelOpen] = useState(true)

  useEffect(() => {
    const section = findActiveSection(location.pathname, items)
    if (section) {
      setActiveSection(section)
      const item = items.find(i => i.title === section)
      setPanelOpen(!!item?.items?.length)
    }
  }, [location.pathname, items])

  const activeItem = useMemo(() => items.find(item => item.title === activeSection) ?? null, [items, activeSection])
  const activeItemIndex = activeItem ? items.findIndex(item => item.title === activeItem.title) : -1
  const showPanel = panelOpen && !!activeItem?.items?.length

  const handlePrimaryClick = (item: DualTierNavItem) => {
    if (item.target === '_blank' || item.url.startsWith('http')) {
      window.open(item.url, item.target || '_blank', 'noopener,noreferrer')
      return
    }

    setActiveSection(item.title)

    if (item.items?.length) {
      if (activeSection === item.title && panelOpen) {
        setPanelOpen(false)
        return
      }
      setPanelOpen(true)
      if (!isItemActive(location.pathname, item, true)) {
        navigate(item.url)
      }
      return
    }

    setPanelOpen(false)
    navigate(item.url)
    onNavigate?.()
  }

  const RailButton = ({ item, active, index }: { item: DualTierNavItem; active: boolean; index: string }) => {
    const Icon = item.icon
    return (
      <TooltipProvider delayDuration={200}>
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              type="button"
              onClick={() => handlePrimaryClick(item)}
              className={cn(
                'group relative flex h-14 w-14 cursor-pointer items-center justify-center rounded-none border transition-colors duration-150 outline-none motion-reduce:transition-none',
                'focus-visible:ring-sidebar-ring focus-visible:ring-offset-sidebar focus-visible:ring-2 focus-visible:ring-offset-2',
                active
                  ? 'border-sidebar-border bg-sidebar-primary text-sidebar-primary-foreground'
                  : 'text-sidebar-foreground/70 hover:border-sidebar-border hover:bg-sidebar-accent hover:text-sidebar-accent-foreground border-transparent',
              )}
              aria-current={active ? 'page' : undefined}
              aria-expanded={active && !!item.items?.length ? showPanel : undefined}
              aria-label={t(item.title)}
            >
              <span className={cn('absolute start-1.5 top-1.5 font-mono text-[8px] font-bold tabular-nums', active ? 'opacity-75' : 'opacity-40')} aria-hidden="true">
                {index}
              </span>
              <Icon className="mt-1 h-5 w-5" />
              <span
                className={cn(
                  'absolute inset-y-1 end-0 w-1 transition-colors motion-reduce:transition-none',
                  active ? 'bg-sidebar-primary-foreground' : 'group-hover:bg-sidebar-primary/50 bg-transparent',
                )}
                aria-hidden="true"
              />
              {item.badge != null && (
                <span className="bg-primary text-primary-foreground absolute -top-1 -right-1 flex h-4 min-w-4 items-center justify-center rounded-full px-1 text-[10px] font-bold">{item.badge}</span>
              )}
            </button>
          </TooltipTrigger>
          <TooltipContent side={side === 'left' ? 'right' : 'left'}>
            <p>{t(item.title)}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    )
  }

  return (
    <aside
      className={cn(
        'bg-sidebar text-sidebar-foreground border-sidebar-border sticky top-0 z-20 flex h-svh shrink-0 overflow-hidden border-r-2',
        side === 'right' && 'border-r-0 border-l-2',
        className,
      )}
    >
      {/* Primary icon rail */}
      <div className={cn('border-sidebar-border/80 bg-sidebar-accent/15 flex w-[5rem] shrink-0 flex-col items-center gap-1 py-3', side === 'left' ? 'border-r-2' : 'order-2 border-l-2')}>
        {header && <div className="mb-2 flex w-full justify-center px-2">{header}</div>}

        <ScrollArea className="min-h-0 w-full flex-1 px-2">
          <div className="flex flex-col items-center gap-2 py-1">
            {items.map((item, index) => {
              const active =
                activeSection === item.title || isItemActive(location.pathname, item, !!item.items?.length) || !!item.items?.some(sub => isItemActive(location.pathname, sub, sub.matchPrefix ?? true))
              return <RailButton key={item.title} item={item} active={active} index={String(index + 1).padStart(2, '0')} />
            })}
          </div>
        </ScrollArea>

        {footerItems.length > 0 && (
          <div className="border-sidebar-border/80 mt-auto flex w-full flex-col items-center gap-1.5 border-t px-2 pt-3">
            {footerItems.map((item, index) => {
              const active = isItemActive(location.pathname, item, true)
              return <RailButton key={item.title} item={item} active={active} index={`A${index + 1}`} />
            })}
          </div>
        )}

        {footer && <div className="mt-2 flex w-full justify-center px-2">{footer}</div>}
      </div>

      {/* Secondary tier panel */}
      <AnimatePresence initial={false} mode="popLayout">
        {showPanel && activeItem?.items && (
          <motion.div
            key={activeItem.title}
            initial={{ width: 0, opacity: 0, x: side === 'left' ? -16 : 16 }}
            animate={{ width: 256, opacity: 1, x: 0 }}
            exit={{ width: 0, opacity: 0, x: side === 'left' ? -16 : 16 }}
            transition={{ type: 'spring', stiffness: 380, damping: 32, mass: 0.8 }}
            className={cn('border-sidebar-border/60 relative h-full overflow-hidden', side === 'left' ? 'border-r-2' : 'order-1 border-l-2')}
          >
            <div className="flex h-full w-64 flex-col">
              <div className="border-sidebar-border/60 relative overflow-hidden border-b-2 px-4 py-5">
                <div className="bg-sidebar-primary absolute end-0 top-0 h-1 w-16" aria-hidden="true" />
                <p className="text-sidebar-foreground/50 font-mono text-[9px] font-bold tracking-[0.18em] uppercase">HPXPANEL // Sector {String(activeItemIndex + 1).padStart(2, '0')}</p>
                <h2 className="font-display mt-2 text-lg leading-none font-black tracking-[0.04em] uppercase">{t(activeItem.title)}</h2>
                <p className="text-sidebar-foreground/40 mt-2 font-mono text-[9px] tracking-[0.12em] uppercase">{activeItem.items.length} modules online</p>
              </div>

              <ScrollArea className="min-h-0 flex-1 px-2 py-3">
                <nav className="flex flex-col gap-1">
                  {activeItem.items.map((sub, index) => {
                    const Icon = sub.icon
                    const active = isItemActive(location.pathname, sub, sub.matchPrefix ?? true)
                    const content = (
                      <motion.div
                        initial={{ opacity: 0, x: side === 'left' ? -10 : 10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.045 * index, duration: 0.22, ease: 'easeOut' }}
                        className={cn(
                          'group flex min-h-12 items-center gap-2.5 rounded-none border px-3 py-2.5 text-sm transition-colors outline-none motion-reduce:transition-none',
                          active
                            ? cn(
                                'border-sidebar-border bg-sidebar-accent text-sidebar-accent-foreground font-bold',
                                side === 'left' ? 'shadow-[inset_3px_0_0_0_hsl(var(--sidebar-primary))]' : 'shadow-[inset_-3px_0_0_0_hsl(var(--sidebar-primary))]',
                              )
                            : 'text-sidebar-foreground/75 hover:border-sidebar-border hover:bg-sidebar-accent/70 hover:text-sidebar-accent-foreground border-transparent',
                        )}
                      >
                        <span className="text-sidebar-foreground/40 w-5 shrink-0 font-mono text-[9px] font-bold tabular-nums">{String(index + 1).padStart(2, '0')}</span>
                        <Icon className="h-4 w-4 shrink-0" />
                        <span className="min-w-0 flex-1 truncate">{t(sub.title)}</span>
                        {sub.badge != null && (
                          <Badge variant="secondary" className="h-5 min-w-5 justify-center rounded-full px-1.5 text-[10px]">
                            {sub.badge}
                          </Badge>
                        )}
                      </motion.div>
                    )

                    if (sub.target === '_blank' || sub.url.startsWith('http')) {
                      return (
                        <a
                          key={sub.title}
                          href={sub.url}
                          target={sub.target || '_blank'}
                          rel="noopener noreferrer"
                          className="focus-visible:ring-ring block outline-none focus-visible:ring-2 focus-visible:ring-inset"
                        >
                          {content}
                        </a>
                      )
                    }

                    return (
                      <NavLink
                        key={sub.title}
                        to={sub.url}
                        end={!sub.matchPrefix}
                        onClick={() => onNavigate?.()}
                        className="focus-visible:ring-ring block outline-none focus-visible:ring-2 focus-visible:ring-inset"
                      >
                        {content}
                      </NavLink>
                    )
                  })}
                </nav>
              </ScrollArea>

              {featureCard && <div className="mt-auto hidden p-3 lg:block">{featureCard}</div>}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </aside>
  )
}
