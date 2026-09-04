import { Language } from '@/components/common/language'
import { ThemeToggle } from '@/components/common/theme-toggle'
import { GithubStar } from '@/components/layout/github-star'
import { GoalProgress } from '@/components/layout/goal-progress'
import { DualTierFeatureCard } from '@/components/layout/dual-tier-feature-card'
import { SidebarDualTier } from '@/components/layout/sidebar-dual-tier'
import { NavMain } from '@/components/layout/nav-main'
import { NavSecondary } from '@/components/layout/nav-secondary'
import { NavUser } from '@/components/layout/nav-user'
import { SidebarTriggerWithBadge } from '@/components/layout/sidebar-trigger-with-badge'
import { VersionBadge } from '@/components/layout/version-badge'
import { Sidebar, SidebarContent, SidebarFooter, SidebarHeader, SidebarMenu, SidebarMenuButton, SidebarMenuItem, useSidebar } from '@/components/ui/sidebar'
import { HPX_LOGO_URL } from '@/constants/brand'
import { DOCUMENTATION, DONATION_URL, REPO_URL } from '@/constants/Project'
import { useAdmin } from '@/hooks/use-admin'
import useDirDetection from '@/hooks/use-dir-detection'
import { useSystemVersion } from '@/hooks/use-system-version'
import { useVersionCheck } from '@/hooks/use-version-check'
import { cn } from '@/lib/utils'
import { useGetSystemUsersStats } from '@/service/api'
import { canReadResourcePage, hasPermission, hasScopeAll, isOwner } from '@/utils/rbac'
import {
  ArrowUpDown,
  Bell,
  BookOpen,
  Calendar,
  Cpu,
  Database,
  FileCode2,
  FileClock,
  FileUser,
  Fingerprint,
  GithubIcon,
  Group,
  HardDriveDownload,
  Key,
  Layers,
  LayoutDashboardIcon,
  LayoutTemplate,
  Activity,
  LifeBuoy,
  ListTodo,
  Lock,
  Logs,
  Network,
  Palette,
  PieChart,
  Radar,
  Send,
  Settings,
  Settings2,
  Share2Icon,
  UserCog,
  UserKey,
  UserPlus,
  UsersIcon,
  Webhook,
  Zap,
} from 'lucide-react'
import * as React from 'react'
import { useCallback, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router'

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const isRTL = useDirDetection() === 'rtl'
  const { t } = useTranslation()
  const { admin } = useAdmin()
  const canReadSystem = hasPermission(admin, 'system', 'read')
  const canReadHosts = canReadResourcePage(admin, 'hosts')
  const canReadGroups = canReadResourcePage(admin, 'groups')
  const canReadAdmins = canReadResourcePage(admin, 'admins')
  const canReadApiKeys = canReadResourcePage(admin, 'api_keys')
  const canReadNodes = canReadResourcePage(admin, 'nodes')
  const canReadCores = canReadResourcePage(admin, 'cores')
  const canReadTemplates = canReadResourcePage(admin, 'templates')
  const canReadClientTemplates = canReadResourcePage(admin, 'client_templates')
  const canReadHpxTunnels = canReadResourcePage(admin, 'hpx_tunnels')
  const canReadHpxPulse = canReadResourcePage(admin, 'hpx_pulse')
  const canReadFleet = canReadNodes || canReadSystem
  const canReadAudit = hasPermission(admin, 'audit_logs', 'read')
  const canReadNodeLogs = hasPermission(admin, 'nodes', 'logs')
  const canBulkCreateFromTemplate = hasPermission(admin, 'users', 'create') && canReadTemplates
  const canBulkUpdateUsers = hasScopeAll(admin, 'users', 'update')
  const nodeNavItems = [
    ...(canReadNodes
      ? [
          {
            title: 'nodes.title',
            url: '/nodes',
            icon: Share2Icon,
          },
        ]
      : []),
    ...(canReadCores
      ? [
          {
            title: 'settings.cores.title',
            url: '/nodes/cores',
            icon: Cpu,
            matchPrefix: true,
          },
          {
            title: 'nodes.wireguard.title',
            url: '/nodes/wireguard',
            icon: Network,
          },
        ]
      : []),
    ...(canReadNodeLogs
      ? [
          {
            title: 'nodes.logs.title',
            url: '/nodes/logs',
            icon: Logs,
          },
        ]
      : []),
  ]
  const templateNavItems = [
    ...(canReadTemplates
      ? [
          {
            title: 'templates.userTemplates',
            url: '/templates/user',
            icon: FileUser,
          },
        ]
      : []),
    ...(canReadClientTemplates
      ? [
          {
            title: 'templates.clientTemplates',
            url: '/templates/client',
            icon: FileCode2,
          },
        ]
      : []),
  ]
  const { currentVersion: systemVersion } = useSystemVersion({ enabled: canReadSystem })
  const { setOpenMobile, openMobile, isMobile } = useSidebar()
  const navigate = useNavigate()
  const displayVersion = canReadSystem && systemVersion ? `(v${systemVersion})` : ''
  const { hasUpdate } = useVersionCheck(systemVersion ?? null, { enabled: canReadSystem })
  const { data: usersStats } = useGetSystemUsersStats(undefined, {
    query: { enabled: canReadSystem, refetchInterval: 30_000, staleTime: 15_000 },
  })
  const activeUsersPercent = usersStats?.total_user && usersStats.total_user > 0 ? Math.round((usersStats.active_users / usersStats.total_user) * 100) : 0
  const touchStartX = useRef<number | null>(null)
  const touchEndX = useRef<number | null>(null)
  const minSwipeDistance = 50
  const edgeThreshold = 50 // Distance from edge to detect edge swipe

  const handleTouchStart = (e: TouchEvent) => {
    touchEndX.current = null
    touchStartX.current = e.touches[0].clientX
  }

  const handleTouchMove = (e: TouchEvent) => {
    touchEndX.current = e.touches[0].clientX
  }

  const handleTouchEnd = useCallback(() => {
    if (!touchStartX.current || !touchEndX.current) return

    const distance = touchStartX.current - touchEndX.current
    const isLeftSwipe = distance > minSwipeDistance
    const isRightSwipe = distance < -minSwipeDistance
    const isFromRightEdge = touchStartX.current > window.innerWidth - edgeThreshold

    // Only handle swipes that start from the right edge
    if (isFromRightEdge) {
      if (isLeftSwipe && !openMobile) {
        setOpenMobile(true)
      } else if (isRightSwipe && openMobile) {
        setOpenMobile(false)
      }
    }

    // Reset touch positions
    touchStartX.current = null
    touchEndX.current = null
  }, [openMobile, setOpenMobile])

  useEffect(() => {
    // Add touch event listeners to the document
    document.addEventListener('touchstart', handleTouchStart, { passive: true })
    document.addEventListener('touchmove', handleTouchMove, { passive: true })
    document.addEventListener('touchend', handleTouchEnd)

    // Cleanup
    return () => {
      document.removeEventListener('touchstart', handleTouchStart)
      document.removeEventListener('touchmove', handleTouchMove)
      document.removeEventListener('touchend', handleTouchEnd)
    }
  }, [handleTouchEnd])

  const data = {
    user: {
      name: admin?.username || 'Admin',
    },
    navMain: [
      ...(canReadSystem
        ? [
            {
              title: 'dashboard',
              url: '/',
              icon: LayoutDashboardIcon,
            },
          ]
        : []),
      ...(hasPermission(admin, 'users', 'read')
        ? [
            {
              title: 'users',
              url: '/users',
              icon: UsersIcon,
            },
          ]
        : []),
      ...(hasPermission(admin, 'nodes', 'stats')
        ? [
            {
              title: 'statistics',
              url: '/statistics',
              icon: PieChart,
            },
            {
              title: 'observability.title',
              url: '/observability',
              icon: Activity,
            },
          ]
        : []),
      ...(canReadFleet
        ? [
            {
              title: 'fleet.title',
              url: '/fleet',
              icon: Network,
            },
          ]
        : []),
      ...(canReadHpxTunnels
        ? [
            {
              title: 'hpxTunnel.title',
              url: '/hpx-tunnel',
              icon: Radar,
            },
          ]
        : []),
      ...(canReadHpxPulse
        ? [
            {
              title: 'hpxPulse.title',
              url: '/hpx-pulse',
              icon: Zap,
            },
          ]
        : []),
      ...(canReadHosts
        ? [
            {
              title: 'hosts',
              url: '/hosts',
              icon: ListTodo,
            },
          ]
        : []),
      ...(canReadGroups
        ? [
            {
              title: 'groups',
              url: '/groups',
              icon: Group,
            },
          ]
        : []),
      ...(canReadAdmins
        ? [
            {
              title: 'admins.title',
              url: '/admins',
              icon: UserCog,
            },
          ]
        : []),
      ...(isOwner(admin)
        ? [
            {
              title: 'adminRoles.title',
              url: '/admin-roles',
              icon: UserKey,
            },
          ]
        : []),
      ...(canReadApiKeys
        ? [
            {
              title: 'apiKeys.title',
              url: '/api-keys',
              icon: Key,
            },
          ]
        : []),
      ...(canReadAudit
        ? [
            {
              title: 'audit.title',
              url: '/audit',
              icon: FileClock,
            },
          ]
        : []),
      ...(nodeNavItems.length > 0
        ? [
            {
              title: 'nodes.title',
              url: nodeNavItems[0].url,
              icon: Share2Icon,
              items: nodeNavItems,
            },
          ]
        : []),
      ...(templateNavItems.length > 0
        ? [
            {
              title: 'templates.title',
              url: templateNavItems[0].url,
              icon: LayoutTemplate,
              items: templateNavItems,
            },
          ]
        : []),
      ...(canBulkCreateFromTemplate || canBulkUpdateUsers
        ? [
            {
              title: 'bulk.title',
              url: '/bulk',
              icon: Layers,
              items: [
                ...(canBulkCreateFromTemplate
                  ? [
                      {
                        title: 'bulk.createUsers',
                        url: '/bulk',
                        icon: UserPlus,
                      },
                    ]
                  : []),
                ...(canBulkUpdateUsers
                  ? [
                      {
                        title: 'bulk.groups',
                        url: '/bulk/groups',
                        icon: Group,
                      },
                      {
                        title: 'bulk.expireDate',
                        url: '/bulk/expire',
                        icon: Calendar,
                      },
                      {
                        title: 'bulk.dataLimit',
                        url: '/bulk/data',
                        icon: ArrowUpDown,
                      },
                      {
                        title: 'bulk.proxySettings',
                        url: '/bulk/proxy',
                        icon: Lock,
                      },
                    ]
                  : []),
              ],
            },
          ]
        : []),
      {
        title: 'settings.title',
        url: '/settings',
        icon: Settings2,
        items: [
          ...(hasPermission(admin, 'settings', 'read_general') && hasPermission(admin, 'settings', 'update')
            ? [
                {
                  title: 'settings.general.title',
                  url: '/settings/general',
                  icon: Settings,
                },
              ]
            : []),
          ...(hasPermission(admin, 'settings', 'read') && hasPermission(admin, 'settings', 'update')
            ? [
                {
                  title: 'settings.notifications.title',
                  url: '/settings/notifications',
                  icon: Bell,
                },
                {
                  title: 'settings.subscriptions.title',
                  url: '/settings/subscriptions',
                  icon: ListTodo,
                },
                {
                  title: 'settings.hwid.title',
                  url: '/settings/hwid',
                  icon: Fingerprint,
                },
                {
                  title: 'settings.telegram.title',
                  url: '/settings/telegram',
                  icon: Send,
                },
                {
                  title: 'settings.webhook.title',
                  url: '/settings/webhook',
                  icon: Webhook,
                },
                {
                  title: 'settings.cleanup.title',
                  url: '/settings/cleanup',
                  icon: Database,
                },
                {
                  title: 'settings.backup.title',
                  url: '/settings/backup',
                  icon: HardDriveDownload,
                },
              ]
            : []),
          {
            title: 'theme.title',
            url: '/settings/theme',
            icon: Palette,
          },
        ],
      },
    ],
    navSecondary: [
      {
        title: t('supportUs'),
        url: DONATION_URL,
        icon: LifeBuoy,
        target: '_blank',
      },
    ],
    community: [
      {
        title: 'documentation',
        url: DOCUMENTATION,
        icon: BookOpen,
        target: '_blank',
      },
      {
        title: 'github',
        url: REPO_URL,
        icon: GithubIcon,
        target: '_blank',
      },
    ],
  }

  const brandMark = (
    <Link
      to="/"
      className="relative flex h-11 w-11 items-center justify-center overflow-hidden border-2 border-[hsl(var(--pixel-border))] shadow-[3px_3px_0_0_hsl(var(--pixel-border))]"
      aria-label="HPXPANEL home"
    >
      <img src={HPX_LOGO_URL} alt="HPXPANEL" className="h-full w-full object-cover" draggable={false} />
      {canReadSystem && <VersionBadge currentVersion={systemVersion ?? null} compact className="z-10" />}
    </Link>
  )

  const dualTierFooterItems = [
    ...(isOwner(admin)
      ? data.community.map(item => ({
          title: item.title,
          url: item.url,
          icon: item.icon,
          target: item.target,
        }))
      : []),
    {
      title: 'supportUs',
      url: DONATION_URL,
      icon: LifeBuoy,
      target: '_blank' as const,
    },
  ]

  // Desktop: HPXPANEL indexed sector rail + secondary module panel
  if (!isMobile) {
    return (
      <SidebarDualTier
        side={isRTL ? 'right' : 'left'}
        items={data.navMain}
        footerItems={dualTierFooterItems}
        header={brandMark}
        footer={<NavUser admin={admin} username={data.user} />}
        featureCard={
          canReadSystem ? (
            <DualTierFeatureCard title={t('statistics.activeUsers')} description={t('monitorUsers')} progress={activeUsersPercent} confirmLabel={t('users')} onConfirm={() => navigate('/users')} />
          ) : undefined
        }
      />
    )
  }

  return (
    <>
      <div className="sticky top-0 z-30 lg:hidden">
        <div className="bg-sidebar h-[env(safe-area-inset-top)]" />
        <div className="border-sidebar-border bg-sidebar/90 supports-[backdrop-filter]:bg-sidebar/75 flex items-center justify-between border-b px-4 py-3.5 backdrop-blur-xl">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center overflow-hidden border-2 border-[hsl(var(--pixel-border))] shadow-[2px_2px_0_0_hsl(var(--pixel-border))]">
              <img src={HPX_LOGO_URL} alt="HPXPANEL" className="h-full w-full object-cover" draggable={false} />
            </div>
            <div dir={isRTL ? 'rtl' : 'ltr'} className="leading-tight">
              <span className="font-display block text-sm font-black tracking-[0.08em]">HPXPANEL</span>
              <span className="text-sidebar-foreground/45 font-mono text-[9px] font-bold tracking-[0.16em] uppercase">Control // online</span>
            </div>
          </Link>
          <SidebarTriggerWithBadge showUpdateBadge={canReadSystem && hasUpdate} />
        </div>
      </div>
      <Sidebar variant="sidebar" collapsible="offcanvas" {...props} className="border-sidebar-border bg-sidebar p-0" side={isRTL ? 'right' : 'left'}>
        <SidebarHeader className="border-sidebar-border/70 border-b">
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton size="lg" asChild className="!gap-2">
                <Link to="/">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center overflow-hidden border-2 border-[hsl(var(--pixel-border))]">
                    <img src={HPX_LOGO_URL} alt="HPXPANEL" className="h-full w-full object-cover" draggable={false} />
                  </div>
                  <div className="flex min-w-0 flex-col overflow-hidden">
                    <span className={cn(isRTL ? 'text-right' : 'text-left', 'font-display truncate text-sm leading-tight font-black tracking-[0.08em]')}>HPXPANEL</span>
                    <span className="max-w-full truncate font-mono text-[9px] leading-none tracking-[0.12em] uppercase opacity-45">Sector control {displayVersion}</span>
                  </div>
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarHeader>
        <SidebarContent>
          <NavMain items={data.navMain} />
          {isOwner(admin) && <NavSecondary items={data.community} label={t('community')} />}
          <NavSecondary items={data.navSecondary} className="mt-auto" />
          <GoalProgress />
          <div className="flex items-center justify-between px-2 [&>:first-child]:[direction:ltr]">
            <GithubStar />
            <div className="flex items-start gap-2">
              <Language />
              <ThemeToggle />
            </div>
          </div>
        </SidebarContent>
        <SidebarFooter>
          <NavUser admin={admin} username={data?.user} />
        </SidebarFooter>
      </Sidebar>
    </>
  )
}
