import type { LucideIcon } from 'lucide-react'
import { ChevronDown } from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { NavLink, useLocation, useNavigate } from 'react-router'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
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

export function SidebarHoverRail({ items, footerItems = [], header, footer, featureCard, side = 'left', className }: SidebarHoverRailProps) {
  const { t } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()
  const [hovered, setHovered] = useState(false)
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

  const expanded = hovered

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
          'flex h-9 w-full items-center gap-2.5 rounded-lg px-2.5 text-[13px] font-medium transition-[background-color,color,box-shadow] duration-150 ease-out',
          nested && 'h-8 ps-9 text-[12px]',
          active
            ? 'bg-sidebar-accent text-sidebar-accent-foreground shadow-[inset_2px_0_0_0_hsl(var(--sidebar-primary))]'
            : 'text-sidebar-foreground/75 hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground',
        )}
      >
        <Icon className={cn('shrink-0', nested ? 'h-3.5 w-3.5' : 'h-4 w-4')} />
        <span
          className={cn(
            'truncate whitespace-nowrap transition-[opacity,width] duration-200 ease-out',
            expanded ? 'w-auto opacity-100' : 'pointer-events-none w-0 opacity-0',
          )}
        >
          {label}
        </span>
        {'badge' in item && item.badge != null && expanded && (
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

    const iconButton = (
      <span
        className={cn(
          'flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors duration-150',
          active ? 'bg-sidebar-primary text-sidebar-primary-foreground' : 'text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
        )}
      >
        <Icon className="h-4 w-4" />
      </span>
    )

    if (!hasChildren) {
      if (!expanded) {
        return (
          <TooltipProvider delayDuration={120}>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="flex justify-center px-1.5">
                  {item.target === '_blank' || item.url.startsWith('http') ? (
                    <a href={item.url} target={item.target || '_blank'} rel="noopener noreferrer">
                      {iconButton}
                    </a>
                  ) : (
                    <NavLink to={item.url}>{iconButton}</NavLink>
                  )}
                </div>
              </TooltipTrigger>
              <TooltipContent side={side === 'left' ? 'right' : 'left'}>{t(item.title)}</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )
      }
      return (
        <div className="px-2">
          <NavRow item={item} />
        </div>
      )
    }

    if (!expanded) {
      return (
        <TooltipProvider delayDuration={120}>
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                className="mx-auto flex justify-center px-1.5 outline-none"
                onClick={() => {
                  navigate(item.url)
                }}
              >
                {iconButton}
              </button>
            </TooltipTrigger>
            <TooltipContent side={side === 'left' ? 'right' : 'left'}>{t(item.title)}</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      )
    }

    return (
      <Collapsible open={sectionOpen} onOpenChange={() => toggleSection(item.title)} className="px-2">
        <div className="flex items-center gap-0.5">
          <CollapsibleTrigger asChild>
            <button type="button" className="flex min-w-0 flex-1 items-center outline-none" onClick={() => !sectionOpen && navigate(item.url)}>
              <span
                className={cn(
                  'flex h-9 w-full items-center gap-2.5 rounded-lg px-2.5 text-[13px] font-medium transition-colors duration-150',
                  active ? 'bg-sidebar-accent/80 text-sidebar-accent-foreground' : 'text-sidebar-foreground/75 hover:bg-sidebar-accent/50',
                )}
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span className="truncate">{t(item.title)}</span>
                <ChevronDown className={cn('text-muted-foreground ms-auto h-3.5 w-3.5 transition-transform duration-200', sectionOpen && 'rotate-180')} />
              </span>
            </button>
          </CollapsibleTrigger>
        </div>
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

  const widthClass = expanded ? 'w-[15.5rem]' : 'w-[3.75rem]'

  return (
    <aside
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className={cn(
        'bg-sidebar text-sidebar-foreground border-sidebar-border sticky top-0 z-20 flex h-svh shrink-0 flex-col overflow-hidden border-r transition-[width] duration-200 ease-[cubic-bezier(0.22,1,0.36,1)] will-change-[width]',
        side === 'right' && 'border-r-0 border-l',
        widthClass,
        className,
      )}
    >
      {header && <div className={cn('flex shrink-0 py-3', expanded ? 'px-3' : 'justify-center px-2')}>{header}</div>}

      <ScrollArea className="min-h-0 flex-1">
        <nav className="flex flex-col gap-1 py-1">{items.map(item => <PrimaryItem key={item.title} item={item} />)}</nav>
      </ScrollArea>

      {footerItems.length > 0 && (
        <div className="border-sidebar-border/80 flex flex-col gap-1 border-t py-2">
          {footerItems.map(item => (
            <PrimaryItem key={item.title} item={item} />
          ))}
        </div>
      )}

      {expanded && featureCard && <div className="hidden p-3 lg:block">{featureCard}</div>}
      {footer && <div className={cn('mt-auto shrink-0 pb-3', expanded ? 'px-3' : 'flex justify-center px-2')}>{footer}</div>}
    </aside>
  )
}
