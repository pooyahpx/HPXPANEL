import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router'
import type { LucideIcon } from 'lucide-react'
import {
  Activity,
  Group,
  HardDriveDownload,
  LayoutDashboardIcon,
  LayoutTemplate,
  ListTodo,
  Palette,
  PieChart,
  Settings2,
  Share2Icon,
  UserCog,
  UsersIcon,
  Key,
  Layers,
  Bell,
  Database,
  Cpu,
  Search,
  Zap,
  Paintbrush,
  X,
} from 'lucide-react'
import { useAdmin } from '@/hooks/use-admin'
import { cn } from '@/lib/utils'
import { canReadResourcePage, hasPermission, isOwner } from '@/utils/rbac'
import { Button } from '@/components/ui/button'

type QuestItem = {
  id: string
  title: string
  url: string
  icon: LucideIcon
  keywords?: string
}

function useQuestItems(): QuestItem[] {
  const { admin } = useAdmin()

  return useMemo(() => {
    const items: QuestItem[] = []

    if (hasPermission(admin, 'system', 'read')) {
      items.push({ id: 'dashboard', title: 'dashboard', url: '/', icon: LayoutDashboardIcon, keywords: 'home overview' })
    }
    if (hasPermission(admin, 'users', 'read')) {
      items.push({ id: 'users', title: 'users', url: '/users', icon: UsersIcon, keywords: 'accounts clients' })
    }
    if (hasPermission(admin, 'nodes', 'stats')) {
      items.push({ id: 'statistics', title: 'statistics', url: '/statistics', icon: PieChart, keywords: 'charts traffic' })
      items.push({ id: 'observability', title: 'observability.title', url: '/observability', icon: Activity, keywords: 'noc health alerts prometheus' })
    }
    if (canReadResourcePage(admin, 'hosts')) {
      items.push({ id: 'hosts', title: 'hosts', url: '/hosts', icon: ListTodo })
    }
    if (canReadResourcePage(admin, 'groups')) {
      items.push({ id: 'groups', title: 'groups', url: '/groups', icon: Group })
    }
    if (canReadResourcePage(admin, 'admins')) {
      items.push({ id: 'admins', title: 'admins.title', url: '/admins', icon: UserCog })
    }
    if (canReadResourcePage(admin, 'api_keys')) {
      items.push({ id: 'api-keys', title: 'apiKeys.title', url: '/api-keys', icon: Key })
    }
    if (canReadResourcePage(admin, 'nodes')) {
      items.push({ id: 'nodes', title: 'nodes.title', url: '/nodes', icon: Share2Icon, keywords: 'servers' })
    }
    if (canReadResourcePage(admin, 'hpx_pulse') || canReadResourcePage(admin, 'hpx_tunnels')) {
      items.push({
        id: 'hpx-pulse',
        title: 'hpxPulse.title',
        url: '/hpx-pulse',
        icon: Zap,
        keywords: 'pulse icmp tunnel ping hpx',
      })
    }
    if (canReadResourcePage(admin, 'cores')) {
      items.push({ id: 'cores', title: 'settings.cores.title', url: '/nodes/cores', icon: Cpu })
    }
    if (canReadResourcePage(admin, 'templates')) {
      items.push({ id: 'templates', title: 'templates.title', url: '/templates/user', icon: LayoutTemplate })
    }
    if (hasPermission(admin, 'settings', 'read') && hasPermission(admin, 'settings', 'update')) {
      items.push({ id: 'sub-theme', title: 'subTheme.title', url: '/sub-theme', icon: Paintbrush, keywords: 'subscription page skin appearance theme' })
    }
    if (hasPermission(admin, 'users', 'create') && canReadResourcePage(admin, 'templates')) {
      items.push({ id: 'bulk', title: 'bulk.title', url: '/bulk', icon: Layers })
    }
    if (hasPermission(admin, 'settings', 'read') || hasPermission(admin, 'settings', 'read_general') || isOwner(admin)) {
      items.push({ id: 'settings', title: 'settings.title', url: '/settings', icon: Settings2 })
      items.push({ id: 'notifications', title: 'settings.notifications.title', url: '/settings/notifications', icon: Bell })
      items.push({ id: 'cleanup', title: 'settings.cleanup.title', url: '/settings/cleanup', icon: Database })
      items.push({ id: 'backup', title: 'settings.backup.title', url: '/settings/backup', icon: HardDriveDownload, keywords: 'backup restore sftp archive' })
    }
    items.push({ id: 'theme', title: 'theme.title', url: '/settings/theme', icon: Palette })

    return items
  }, [admin])
}

export function QuestSearch({ className, compact }: { className?: string; compact?: boolean }) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const items = useQuestItems()
  const inputRef = useRef<HTMLInputElement>(null)
  const rootRef = useRef<HTMLDivElement>(null)
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [expanded, setExpanded] = useState(!compact)
  const [activeIndex, setActiveIndex] = useState(0)

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return items
    return items.filter(item => {
      const label = t(item.title).toLowerCase()
      return label.includes(q) || item.title.toLowerCase().includes(q) || item.url.toLowerCase().includes(q) || (item.keywords?.includes(q) ?? false)
    })
  }, [items, query, t])

  useEffect(() => {
    setActiveIndex(0)
  }, [query, open])

  const expandAndFocus = useCallback(() => {
    setExpanded(true)
    setOpen(true)
    requestAnimationFrame(() => {
      inputRef.current?.focus()
    })
  }, [])

  const collapseIfIdle = useCallback(() => {
    if (!compact) return
    if (query.trim()) return
    setOpen(false)
    setExpanded(false)
  }, [compact, query])

  const go = useCallback(
    (item: QuestItem) => {
      navigate(item.url)
      setQuery('')
      setOpen(false)
      if (compact) setExpanded(false)
      inputRef.current?.blur()
    },
    [navigate, compact],
  )

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null
      const tag = target?.tagName?.toLowerCase()
      const editable = tag === 'input' || tag === 'textarea' || target?.isContentEditable

      if (e.key === '/' && !editable && !e.metaKey && !e.ctrlKey && !e.altKey) {
        e.preventDefault()
        expandAndFocus()
        return
      }

      if (!open && !expanded) return

      if (e.key === 'Escape') {
        e.preventDefault()
        setOpen(false)
        if (compact && !query.trim()) {
          setExpanded(false)
          inputRef.current?.blur()
        } else {
          inputRef.current?.blur()
        }
        return
      }

      if (!open) return

      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setActiveIndex(i => Math.min(i + 1, Math.max(filtered.length - 1, 0)))
        return
      }

      if (e.key === 'ArrowUp') {
        e.preventDefault()
        setActiveIndex(i => Math.max(i - 1, 0))
        return
      }

      if (e.key === 'Enter' && filtered[activeIndex]) {
        e.preventDefault()
        go(filtered[activeIndex])
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open, expanded, filtered, activeIndex, go, expandAndFocus, compact, query])

  useEffect(() => {
    const onPointerDown = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) {
        setOpen(false)
        collapseIfIdle()
      }
    }
    document.addEventListener('mousedown', onPointerDown)
    return () => document.removeEventListener('mousedown', onPointerDown)
  }, [collapseIfIdle])

  useEffect(() => {
    if (expanded && compact) {
      const id = window.setTimeout(() => inputRef.current?.focus(), 180)
      return () => window.clearTimeout(id)
    }
  }, [expanded, compact])

  const results = open && (
    <div className="bg-popover/95 absolute top-[calc(100%+8px)] start-0 z-50 max-h-80 w-[min(100vw-1.5rem,22rem)] overflow-auto rounded-xl border border-border/70 shadow-[0_16px_40px_-20px_hsl(0_0%_0%/0.65)] backdrop-blur-xl sm:w-[24rem]">
      <div className="bg-muted/50 text-muted-foreground sticky top-0 z-10 flex items-center justify-between border-b border-border/50 px-3 py-2 text-[10px] font-semibold tracking-[0.14em] uppercase">
        <span>Modules</span>
        <span>{String(filtered.length).padStart(2, '0')}</span>
      </div>
      {filtered.length === 0 ? (
        <p className="text-muted-foreground px-3 py-4 text-xs">{t('noResults', { defaultValue: 'No results.' })}</p>
      ) : (
        <ul id="command-index-results" role="listbox" className="py-1">
          {filtered.map((item, index) => {
            const Icon = item.icon
            const active = index === activeIndex
            return (
              <li key={item.id} role="none">
                <button
                  id={`command-index-${item.id}`}
                  type="button"
                  role="option"
                  aria-selected={active}
                  className={cn(
                    'flex min-h-10 w-full cursor-pointer items-center gap-2.5 px-3 py-2 text-start text-xs font-medium outline-none transition-colors duration-150',
                    'focus-visible:ring-ring focus-visible:ring-2 focus-visible:ring-inset',
                    active ? 'bg-primary text-primary-foreground' : 'text-foreground hover:bg-accent hover:text-accent-foreground',
                  )}
                  onMouseEnter={() => setActiveIndex(index)}
                  onClick={() => go(item)}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  <span className="min-w-0 flex-1 truncate">{t(item.title)}</span>
                  <span className={cn('hidden text-[10px] opacity-55 sm:inline', active && 'opacity-80')}>{item.url}</span>
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )

  if (compact) {
    return (
      <div ref={rootRef} className={cn('relative flex items-center', className)}>
        <div
          className={cn(
            'border-border/60 bg-card/55 relative flex h-9 items-center overflow-hidden rounded-xl border backdrop-blur-md',
            'will-change-[width,box-shadow] transition-[width,box-shadow,background-color,border-color] duration-[220ms] ease-[cubic-bezier(0.22,1,0.36,1)]',
            'motion-reduce:transition-none',
            expanded
              ? 'bg-card/70 shadow-[0_10px_28px_-16px_hsl(0_0%_0%/0.55)]'
              : 'hover:bg-card/70 cursor-pointer shadow-none',
          )}
          style={{
            width: expanded ? 'min(22rem, calc(100vw - 8rem))' : '2.25rem',
          }}
          onClick={() => {
            if (!expanded) expandAndFocus()
          }}
        >
          <button
            type="button"
            className="text-foreground/85 hover:text-foreground flex h-full w-9 shrink-0 cursor-pointer items-center justify-center outline-none"
            aria-label={t('search', { defaultValue: 'Search' })}
            aria-expanded={expanded}
            onClick={e => {
              e.stopPropagation()
              if (expanded) {
                inputRef.current?.focus()
                setOpen(true)
              } else {
                expandAndFocus()
              }
            }}
          >
            <Search className="h-4 w-4" />
          </button>
          <input
            id="quest-search-input"
            ref={inputRef}
            className={cn(
              'text-foreground placeholder:text-muted-foreground min-w-0 flex-1 border-0 bg-transparent py-0 text-sm outline-none transition-[opacity,transform] duration-[180ms] ease-out',
              expanded ? 'opacity-100 translate-x-0' : 'pointer-events-none w-0 opacity-0 -translate-x-1',
            )}
            type="text"
            value={query}
            placeholder="Locate a sector, module, or route..."
            tabIndex={expanded ? 0 : -1}
            onChange={e => {
              setQuery(e.target.value)
              setOpen(true)
            }}
            onFocus={() => {
              if (expanded) setOpen(true)
            }}
            autoComplete="off"
            spellCheck={false}
            role="combobox"
            aria-label="Search HPXPANEL modules"
            aria-autocomplete="list"
            aria-expanded={open}
            aria-controls="command-index-results"
            aria-activedescendant={open && filtered[activeIndex] ? `command-index-${filtered[activeIndex].id}` : undefined}
          />
          <kbd
            className={cn(
              'text-muted-foreground me-1 h-6 min-w-6 shrink-0 items-center justify-center rounded-md border border-border/50 px-1.5 font-mono text-[10px] transition-opacity duration-150',
              expanded ? 'hidden opacity-100 sm:inline-flex' : 'hidden opacity-0',
            )}
          >
            /
          </kbd>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            tabIndex={expanded ? 0 : -1}
            className={cn(
              'text-muted-foreground hover:text-foreground me-0.5 h-7 w-7 cursor-pointer rounded-lg transition-[opacity,transform] duration-150',
              expanded ? 'opacity-100 scale-100' : 'pointer-events-none w-0 scale-90 opacity-0',
            )}
            aria-label={t('close', { defaultValue: 'Close' })}
            onClick={e => {
              e.stopPropagation()
              setQuery('')
              setOpen(false)
              setExpanded(false)
            }}
          >
            <X className="h-3.5 w-3.5" />
          </Button>
        </div>
        {expanded && results}
      </div>
    )
  }

  return (
    <div ref={rootRef} className={cn('relative w-full max-w-[520px]', className)}>
      <div className="mb-2 flex items-center justify-between gap-3">
        <label className="text-foreground font-mono text-[11px] font-bold tracking-[0.16em] uppercase" htmlFor="quest-search-input">
          HPXPANEL // Command index
        </label>
        <span className="text-muted-foreground font-mono text-[9px] tracking-[0.16em] uppercase">Directory 00</span>
      </div>

      <div
        className={cn(
          'bg-card text-foreground relative flex h-12 items-center border-2 border-[hsl(var(--pixel-border))] shadow-[3px_3px_0_0_hsl(var(--pixel-border))] transition-[box-shadow,border-color] duration-150',
          'focus-within:border-primary focus-within:shadow-[3px_3px_0_0_hsl(var(--primary))] motion-reduce:transition-none',
        )}
      >
        <span className="bg-foreground text-background flex h-full w-12 shrink-0 items-center justify-center border-e-2 border-[hsl(var(--pixel-border))]">
          <Search className="h-[18px] w-[18px]" aria-hidden="true" />
        </span>
        <input
          id="quest-search-input"
          ref={inputRef}
          className="text-foreground placeholder:text-muted-foreground min-w-0 flex-1 border-0 bg-transparent px-3 py-0 font-mono text-sm font-medium outline-none"
          type="text"
          value={query}
          placeholder="Locate a sector, module, or route..."
          onChange={e => {
            setQuery(e.target.value)
            setOpen(true)
          }}
          onFocus={() => setOpen(true)}
          autoComplete="off"
          spellCheck={false}
          role="combobox"
          aria-label="Search HPXPANEL modules"
          aria-autocomplete="list"
          aria-expanded={open}
          aria-controls="command-index-results"
          aria-activedescendant={open && filtered[activeIndex] ? `command-index-${filtered[activeIndex].id}` : undefined}
        />
        <kbd className="bg-muted text-foreground me-2 inline-flex h-7 min-w-7 shrink-0 items-center justify-center border border-[hsl(var(--pixel-border))] px-2 font-mono text-[11px] leading-none font-bold">
          /
        </kbd>
      </div>

      <p className="text-muted-foreground mt-2 font-mono text-[10px] leading-relaxed tracking-[0.06em] uppercase">
        Press <span className="text-foreground font-bold">/</span> to focus · Arrow keys to scan · Enter to deploy
      </p>

      {results}
    </div>
  )
}
