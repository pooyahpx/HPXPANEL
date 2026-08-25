import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router'
import type { LucideIcon } from 'lucide-react'
import { Group, LayoutDashboardIcon, LayoutTemplate, ListTodo, Palette, PieChart, Radar, Settings2, Share2Icon, UserCog, UsersIcon, Key, Layers, Bell, Database, Cpu, Search } from 'lucide-react'
import { useAdmin } from '@/hooks/use-admin'
import { cn } from '@/lib/utils'
import { canReadResourcePage, hasPermission, isOwner } from '@/utils/rbac'

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
    if (canReadResourcePage(admin, 'hpx_tunnels')) {
      items.push({ id: 'hpx-tunnel', title: 'hpxTunnel.title', url: '/hpx-tunnel', icon: Radar, keywords: 'icmp tunnel ping' })
    }
    if (canReadResourcePage(admin, 'cores')) {
      items.push({ id: 'cores', title: 'settings.cores.title', url: '/nodes/cores', icon: Cpu })
    }
    if (canReadResourcePage(admin, 'templates')) {
      items.push({ id: 'templates', title: 'templates.title', url: '/templates/user', icon: LayoutTemplate })
    }
    if (hasPermission(admin, 'users', 'create') && canReadResourcePage(admin, 'templates')) {
      items.push({ id: 'bulk', title: 'bulk.title', url: '/bulk', icon: Layers })
    }
    if (hasPermission(admin, 'settings', 'read') || hasPermission(admin, 'settings', 'read_general') || isOwner(admin)) {
      items.push({ id: 'settings', title: 'settings.title', url: '/settings', icon: Settings2 })
      items.push({ id: 'notifications', title: 'settings.notifications.title', url: '/settings/notifications', icon: Bell })
      items.push({ id: 'cleanup', title: 'settings.cleanup.title', url: '/settings/cleanup', icon: Database })
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

  const go = useCallback(
    (item: QuestItem) => {
      navigate(item.url)
      setQuery('')
      setOpen(false)
      inputRef.current?.blur()
    },
    [navigate],
  )

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null
      const tag = target?.tagName?.toLowerCase()
      const editable = tag === 'input' || tag === 'textarea' || target?.isContentEditable

      if (e.key === '/' && !editable && !e.metaKey && !e.ctrlKey && !e.altKey) {
        e.preventDefault()
        inputRef.current?.focus()
        setOpen(true)
        return
      }

      if (!open) return

      if (e.key === 'Escape') {
        setOpen(false)
        inputRef.current?.blur()
        return
      }

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
  }, [open, filtered, activeIndex, go])

  useEffect(() => {
    const onPointerDown = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', onPointerDown)
    return () => document.removeEventListener('mousedown', onPointerDown)
  }, [])

  return (
    <div ref={rootRef} className={cn('relative w-full max-w-[520px]', className)}>
      {!compact && (
        <div className="mb-2 flex items-center justify-between gap-3">
          <label className="text-foreground font-mono text-[11px] font-bold tracking-[0.16em] uppercase" htmlFor="quest-search-input">
            HPXPANEL // Command index
          </label>
          <span className="text-muted-foreground font-mono text-[9px] tracking-[0.16em] uppercase">Directory 00</span>
        </div>
      )}

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

      {!compact && (
        <p className="text-muted-foreground mt-2 font-mono text-[10px] leading-relaxed tracking-[0.06em] uppercase">
          Press <span className="text-foreground font-bold">/</span> to focus · Arrow keys to scan · Enter to deploy
        </p>
      )}

      {open && (
        <div className="bg-card absolute top-[calc(100%+8px)] right-0 left-0 z-50 max-h-80 overflow-auto border-2 border-[hsl(var(--pixel-border))] shadow-[4px_4px_0_0_hsl(var(--pixel-border))]">
          <div className="bg-muted/70 text-muted-foreground sticky top-0 z-10 flex items-center justify-between border-b border-[hsl(var(--pixel-border)/0.45)] px-3 py-2 font-mono text-[9px] font-bold tracking-[0.16em] uppercase">
            <span>Available modules</span>
            <span>{String(filtered.length).padStart(2, '0')} indexed</span>
          </div>
          {filtered.length === 0 ? (
            <p className="text-muted-foreground px-3 py-4 font-mono text-xs">{t('noResults', { defaultValue: 'No results.' })}</p>
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
                        'flex min-h-11 w-full items-center gap-3 px-3 py-2.5 text-start font-mono text-xs font-bold tracking-[0.03em] transition-colors outline-none motion-reduce:transition-none',
                        'focus-visible:ring-ring focus-visible:ring-2 focus-visible:ring-inset',
                        active ? 'bg-primary text-primary-foreground' : 'text-foreground hover:bg-accent hover:text-accent-foreground',
                      )}
                      onMouseEnter={() => setActiveIndex(index)}
                      onClick={() => go(item)}
                    >
                      <Icon className="h-4 w-4 shrink-0" />
                      <span className="w-5 shrink-0 text-[9px] tabular-nums opacity-55">{String(index + 1).padStart(2, '0')}</span>
                      <span className="min-w-0 flex-1 truncate">{t(item.title)}</span>
                      <span className={cn('hidden text-[9px] opacity-60 sm:inline', active && 'opacity-80')}>{item.url}</span>
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
