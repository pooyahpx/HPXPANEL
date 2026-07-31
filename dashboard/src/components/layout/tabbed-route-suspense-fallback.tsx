import { LoadingSpinner } from '@/components/common/loading-spinner'
import PageHeader from '@/components/layout/page-header'
import { SectorTabBar, type SectorTab } from '@/components/layout/sector-tab-bar'
import { getDocsUrl } from '@/utils/docs-url'
import { useAdmin } from '@/hooks/use-admin'
import { hasPermission, hasScopeAll } from '@/utils/rbac'
import {
  ArrowUpDown,
  Bell,
  Calendar,
  Cpu,
  Database,
  FileCode2,
  FileUser,
  Fingerprint,
  Group,
  ListTodo,
  Lock,
  Logs,
  Network,
  Palette,
  Send,
  Settings as SettingsIcon,
  Share2,
  UserPlus,
  Webhook,
} from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { useLocation } from 'react-router'

type TabDef = SectorTab

const NODES_TABS: TabDef[] = [
  { id: 'nodes.title', label: 'nodes.title', icon: Share2, url: '/nodes' },
  { id: 'core', label: 'core', mobileLabel: 'settings.cores.title', icon: Cpu, url: '/nodes/cores' },
  { id: 'nodes.wireguard.title', label: 'nodes.wireguard.title', icon: Network, url: '/nodes/wireguard' },
  { id: 'nodes.logs.title', label: 'nodes.logs.title', icon: Logs, url: '/nodes/logs' },
]

const SETTINGS_SUDO_TABS: TabDef[] = [
  { id: 'general', label: 'settings.general.title', icon: SettingsIcon, url: '/settings/general' },
  { id: 'notifications', label: 'settings.notifications.title', icon: Bell, url: '/settings/notifications' },
  { id: 'subscriptions', label: 'settings.subscriptions.title', icon: ListTodo, url: '/settings/subscriptions' },
  { id: 'hwid', label: 'settings.hwid.title', icon: Fingerprint, url: '/settings/hwid' },
  { id: 'telegram', label: 'settings.telegram.title', icon: Send, url: '/settings/telegram' },
  { id: 'webhook', label: 'settings.webhook.title', icon: Webhook, url: '/settings/webhook' },
  { id: 'cleanup', label: 'settings.cleanup.title', icon: Database, url: '/settings/cleanup' },
  { id: 'theme', label: 'theme.title', icon: Palette, url: '/settings/theme' },
]

const SETTINGS_NON_SUDO_TABS: TabDef[] = [{ id: 'theme', label: 'theme.title', icon: Palette, url: '/settings/theme' }]

const BULK_SUDO_TABS: TabDef[] = [
  { id: 'create', label: 'bulk.createUsers', icon: UserPlus, url: '/bulk' },
  { id: 'groups', label: 'bulk.groups', icon: Group, url: '/bulk/groups' },
  { id: 'expire', label: 'bulk.expireDate', icon: Calendar, url: '/bulk/expire' },
  { id: 'data', label: 'bulk.dataLimit', icon: ArrowUpDown, url: '/bulk/data' },
  { id: 'proxy', label: 'bulk.proxySettings', icon: Lock, url: '/bulk/proxy' },
]

const BULK_NON_SUDO_TABS: TabDef[] = [{ id: 'create', label: 'bulk.createUsers', icon: UserPlus, url: '/bulk' }]

const TEMPLATES_TABS: TabDef[] = [
  { id: 'templates.userTemplates', label: 'templates.userTemplates', icon: FileUser, url: '/templates/user' },
  { id: 'templates.clientTemplates', label: 'templates.clientTemplates', icon: FileCode2, url: '/templates/client' },
]

function nodesActiveTabId(pathname: string): string {
  if (pathname.startsWith('/nodes/cores')) return 'core'
  if (pathname.startsWith('/nodes/wireguard')) return 'nodes.wireguard.title'
  if (pathname.startsWith('/nodes/logs')) return 'nodes.logs.title'
  return 'nodes.title'
}

function nodesHeader(pathname: string): { title: string; description: string } {
  if (pathname.startsWith('/nodes/cores')) {
    return { title: 'settings.cores.title', description: 'settings.cores.description' }
  }
  if (pathname.startsWith('/nodes/wireguard')) {
    return { title: 'nodes.wireguard.title', description: 'nodes.wireguard.description' }
  }
  if (pathname.startsWith('/nodes/logs')) {
    return { title: 'nodes.logs.title', description: 'nodes.logs.description' }
  }
  return { title: 'nodes.title', description: 'manageNodes' }
}

function settingsActiveTabId(pathname: string, tabs: TabDef[]): string {
  const hit = tabs.find(t => pathname === t.url)
  return hit?.id ?? tabs[0].id
}

function bulkActiveTabId(pathname: string, tabs: TabDef[]): string {
  const hit = tabs.find(tab => {
    if (tab.id === 'create' && pathname === '/bulk/create') return true
    return pathname === tab.url
  })
  return hit?.id ?? tabs[0].id
}

function bulkHeader(pathname: string): { title: string; description: string } {
  const pathToHeader: Record<string, { title: string; description: string }> = {
    '/bulk': { title: 'bulk.createUsers', description: 'bulk.createUsersDesc' },
    '/bulk/create': { title: 'bulk.createUsers', description: 'bulk.createUsersDesc' },
    '/bulk/groups': { title: 'bulk.groups', description: 'bulk.groupsDesc' },
    '/bulk/expire': { title: 'bulk.expireDate', description: 'bulk.expireDateDesc' },
    '/bulk/data': { title: 'bulk.dataLimit', description: 'bulk.dataLimitDesc' },
    '/bulk/proxy': { title: 'bulk.proxySettings', description: 'bulk.proxySettingsDesc' },
  }
  return pathToHeader[pathname] ?? pathToHeader['/bulk']!
}

function templatesHeader(pathname: string): { title: string; description: string } {
  if (pathname === '/templates/client') {
    return { title: 'clientTemplates.title', description: 'clientTemplates.description' }
  }
  return { title: 'templates.title', description: 'templates.description' }
}

function TabStripPlaceholder({ tabs, activeId, sector, index }: { tabs: TabDef[]; activeId: string; sector: string; index: string }) {
  return <SectorTabBar tabs={tabs} activeId={activeId} sector={sector} index={index} />
}

function ContentSpinner() {
  return (
    <div className="flex min-h-48 flex-1 flex-col items-center justify-center gap-3 px-4 py-10" role="status" aria-busy="true">
      <div className="border-border bg-muted relative h-1.5 w-28 overflow-hidden border">
        <div className="bg-primary absolute inset-y-0 w-1/2 animate-[pulse_0.9s_ease-in-out_infinite]" />
      </div>
    </div>
  )
}

function NodesTabbedFallback({ pathname }: { pathname: string }) {
  const header = nodesHeader(pathname)
  const activeId = nodesActiveTabId(pathname)
  return (
    <div className="flex min-h-0 w-full flex-1 flex-col items-start gap-0">
      <PageHeader title={header.title} description={header.description} tutorialUrl={getDocsUrl(pathname)} />
      <div className="flex min-h-0 w-full flex-1 flex-col">
        <TabStripPlaceholder tabs={NODES_TABS} activeId={activeId} sector="Node grid" index="02" />
        <ContentSpinner />
      </div>
    </div>
  )
}

function SettingsTabbedFallback({ pathname, isSudo }: { pathname: string; isSudo: boolean }) {
  const { t } = useTranslation()
  const tabs = isSudo ? SETTINGS_SUDO_TABS : SETTINGS_NON_SUDO_TABS
  const activeId = settingsActiveTabId(pathname, tabs)
  return (
    <div className="flex w-full flex-col items-start gap-0">
      <PageHeader title={t(`settings.${activeId}.title`)} description="manageSettings" tutorialUrl={getDocsUrl(pathname)} />
      <div className="relative w-full">
        <div className="flex w-full min-w-0 flex-col">
          <TabStripPlaceholder tabs={tabs} activeId={activeId} sector="Control plane" index="04" />
          <ContentSpinner />
        </div>
      </div>
    </div>
  )
}

function BulkTabbedFallback({ pathname, isSudo }: { pathname: string; isSudo: boolean }) {
  const tabs = isSudo ? BULK_SUDO_TABS : BULK_NON_SUDO_TABS
  const activeId = bulkActiveTabId(pathname, tabs)
  const header = bulkHeader(pathname)
  return (
    <div className="flex w-full flex-col items-start gap-0">
      <PageHeader title={header.title} description={header.description} tutorialUrl={getDocsUrl(pathname)} />
      <div className="w-full">
        <TabStripPlaceholder tabs={tabs} activeId={activeId} sector="Batch ops" index="03" />
        <ContentSpinner />
      </div>
    </div>
  )
}

function TemplatesTabbedFallback({ pathname }: { pathname: string }) {
  const header = templatesHeader(pathname)
  const activeId = pathname === '/templates/client' ? 'templates.clientTemplates' : 'templates.userTemplates'
  return (
    <div className="flex w-full flex-col items-start gap-0">
      <PageHeader title={header.title} description={header.description} tutorialUrl={getDocsUrl(pathname)} />
      <div className="w-full">
        <TabStripPlaceholder tabs={TEMPLATES_TABS} activeId={activeId} sector="Blueprints" index="05" />
        <ContentSpinner />
      </div>
    </div>
  )
}

/**
 * Suspense fallback for lazy tabbed layouts: real tab chrome + compact spinner (not full-screen).
 * Mirrors `_dashboard.nodes`, `_dashboard.settings`, `_dashboard.bulk`, `_dashboard.templates`.
 */
export function TabbedRouteSuspenseFallback() {
  const { pathname } = useLocation()
  const { admin } = useAdmin()
  const canUseSettings = (hasPermission(admin, 'settings', 'read') || hasPermission(admin, 'settings', 'read_general')) && hasPermission(admin, 'settings', 'update')
  const canUseBulkAll = hasScopeAll(admin, 'users', 'update')

  if (pathname.startsWith('/nodes')) {
    return <NodesTabbedFallback pathname={pathname} />
  }
  if (pathname.startsWith('/settings')) {
    return <SettingsTabbedFallback pathname={pathname} isSudo={canUseSettings} />
  }
  if (pathname.startsWith('/bulk')) {
    return <BulkTabbedFallback pathname={pathname} isSudo={canUseBulkAll} />
  }
  if (pathname.startsWith('/templates')) {
    return <TemplatesTabbedFallback pathname={pathname} />
  }

  return <LoadingSpinner />
}
