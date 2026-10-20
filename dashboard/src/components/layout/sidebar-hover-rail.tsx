import type { LucideIcon } from 'lucide-react'
import { ChevronDown } from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { NavLink, useLocation, useNavigate } from 'react-router'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'

export type HoverRailSubItem = {
  title: string
  url: string
  icon: LucideIcon
  matchPrefix?: boolean
  badge?: number | string
  target?: string
}

export type HoverRailNavItem = {
  title: string
  url: string
  icon: LucideIcon
  badge?: number | string
  items?: HoverRailSubItem[]
  target?: string
}

type SidebarHoverRailProps = {
  items: HoverRailNavItem[]
  footerItems?: HoverRailNavItem[]
  header?: ReactNode
  footer?: ReactNode
  featureCard?: ReactNode
  side?: 'left' | 'right'
  className?: string
}

function isActive(pathname: string, item: { url: string; matchPrefix?: boolean }, prefix?: boolean) {
  if (item.url.startsWith('http')) return false
  if (item.url === '/') return pathname === '/'
  const usePrefix = prefix ?? item.matchPrefix ?? pathname.startsWith(item.url)
  if (usePrefix) return pathname === item.url || pathname.startsWith(`${item.url}/`)
  return pathname === item.url
}

function sectionOpenByRoute(pathname: string, item: HoverRailNavItem) {
  if (!item.items?.length) return false
  return item.items.some(sub => isActive(pathname, sub, sub.matchPrefix ?? true)) || isActive(pathname, item, true)
}

/** Always-expanded ops rail (labels always visible). */
export function SidebarHoverRail({ items, footerItems = [], header, footer, featureCard, side = 'left', className }: SidebarHoverRailProps) {
  const { t } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({})

  useEffect(() => {
    const next: Record<string, boolean> = {}
    for (const item of items) {
      if (item.items?.length && sectionOpenByRoute(location.pathname, item)) {
        next[item.title] = true
      }
    }
    setOpenSections(prev => ({ ...prev, ...next }))
  }, [location.pathname, items])

  const toggleSection = (title: string) => {
    setOpenSections(prev => ({ ...prev, [title]: !prev[title] }))
  }

  const NavRow = ({ item, nested }: { item: HoverRailSubItem | HoverRailNavItem; nested?: boolean }) => {
    const Icon = item.icon
    const active = isActive(location.pathname, item, 'matchPrefix' in item ? item.matchPrefix : nested)
    const label = t(item.title)

    const inner = (
      <span
        className={cn(
          'flex h-9 w-full cursor-pointer items-center gap-2.5 rounded-xl px-2.5 text-[13px] font-medium transition-[background-color,color,box-shadow] duration-150 ease-out',
          nested && 'h-8 rounded-lg ps-9 text-[12px]',
          active
            ? 'bg-sidebar-primary text-sidebar-primary-foreground shadow-[0_10px_24px_-14px_hsl(var(--sidebar-primary))]'
            : 'text-sidebar-foreground/75 hover:bg-sidebar-accent/70 hover:text-sidebar-accent-foreground',
        )}
      >
        <Icon className={cn('shrink-0', nested ? 'h-3.5 w-3.5' : 'h-4 w-4')} />
        <span className="truncate">{label}</span>
        {'badge' in item && item.badge != null && (
          <Badge variant="secondary" className="ms-auto h-5 min-w-5 justify-center px-1.5 text-[10px]">
            {item.badge}
          </Badge>
        )}
      </span>
    )

    if ('target' in item && (item.target === '_blank' || item.url.startsWith('http'))) {
      return (
        <a href={item.url} target={item.target || '_blank'} rel="noopener noreferrer" className="block outline-none">
          {inner}
        </a>
      )
    }

    return (
      <NavLink to={item.url} end={!nested && !('items' in item)} className="block outline-none focus-visible:ring-2 focus-visible:ring-sidebar-ring">
        {inner}
      </NavLink>
    )
  }

  const PrimaryItem = ({ item }: { item: HoverRailNavItem }) => {
    const Icon = item.icon
    const hasChildren = !!item.items?.length
    const active =
      isActive(location.pathname, item, !!hasChildren) || !!item.items?.some(sub => isActive(location.pathname, sub, sub.matchPrefix ?? true))
    const sectionOpen = openSections[item.title] ?? false

    if (!hasChildren) {
      return (
        <div className="px-2">
          <NavRow item={item} />
        </div>
      )
    }

    return (
      <Collapsible open={sectionOpen} onOpenChange={() => toggleSection(item.title)} className="px-2">
        <CollapsibleTrigger asChild>
          <button
            type="button"
            className="flex w-full min-w-0 items-center outline-none"
            onClick={() => !sectionOpen && navigate(item.url)}
          >
            <span
              className={cn(
                'flex h-9 w-full cursor-pointer items-center gap-2.5 rounded-xl px-2.5 text-[13px] font-medium transition-colors duration-150',
                active
                  ? 'bg-sidebar-primary/90 text-sidebar-primary-foreground shadow-[0_10px_24px_-14px_hsl(var(--sidebar-primary))]'
                  : 'text-sidebar-foreground/75 hover:bg-sidebar-accent/60',
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className="truncate">{t(item.title)}</span>
              <ChevronDown className={cn('ms-auto h-3.5 w-3.5 opacity-70 transition-transform duration-200', sectionOpen && 'rotate-180')} />
            </span>
          </button>
        </CollapsibleTrigger>
        <CollapsibleContent className="data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 space-y-0.5 pt-1 pb-1">
          {item.items!.map(sub => (
            <div key={sub.title}>
              <NavRow item={sub} nested />
            </div>
          ))}
        </CollapsibleContent>
      </Collapsible>
    )
  }

  return (
    <aside
      className={cn(
        'bg-sidebar text-sidebar-foreground border-sidebar-border sticky top-0 z-30 h-svh w-[16.5rem] shrink-0 flex-col overflow-hidden border-r',
        side === 'right' && 'border-r-0 border-l',
        className,
      )}
    >
      {header && <div className="border-sidebar-border/60 flex shrink-0 border-b px-3 py-3.5">{header}</div>}

      <ScrollArea className="min-h-0 flex-1">
        <nav className="flex flex-col gap-0.5 py-2">{items.map(item => <PrimaryItem key={item.title} item={item} />)}</nav>
      </ScrollArea>

      {footerItems.length > 0 && (
        <div className="border-sidebar-border/80 flex flex-col gap-0.5 border-t py-2">
          {footerItems.map(item => (
            <PrimaryItem key={item.title} item={item} />
          ))}
        </div>
      )}

      {featureCard && <div className="shrink-0 px-3 pt-1 pb-2">{featureCard}</div>}
      {footer && (
        <div className="border-sidebar-border/80 mt-auto shrink-0 border-t px-2 py-2.5">{footer}</div>
      )}
    </aside>
  )
}
