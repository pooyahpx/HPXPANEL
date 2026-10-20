import { Footer } from '@/components/layout/footer'
import { AppSidebar } from '@/components/layout/sidebar'
import { PageLoadOverlay } from '@/components/layout/page-load-overlay'
import PageTransition from '@/components/layout/page-transition'
import { QuestSearch } from '@/components/layout/quest-search'
import RouteGuard from '@/components/layout/route-guard'
import { TopLoadingBar } from '@/components/layout/top-loading-bar'
import { VersionUpdateBanner } from '@/components/layout/version-update-banner'
import DonationPopup from '@/components/common/donation-popup'
import { Language } from '@/components/common/language'
import { ThemeToggle } from '@/components/common/theme-toggle'
import { SidebarInset, SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar'
import { getCurrentAdmin } from '@/service/api'
import { Outlet, useLocation } from 'react-router'
import TopbarAd from '@/components/common/topbar-ad'
import { CopilotLauncher } from '@/features/copilot/components/copilot-launcher'
import { useTranslation } from 'react-i18next'

const TITLE_BY_PATH: Array<{ match: (p: string) => boolean; key: string }> = [
  { match: p => p === '/' || p === '', key: 'dashboard' },
  { match: p => p.startsWith('/users'), key: 'users' },
  { match: p => p.startsWith('/nodes'), key: 'nodes.title' },
  { match: p => p.startsWith('/hpx-pulse'), key: 'hpxPulse.title' },
  { match: p => p.startsWith('/hosts'), key: 'hosts' },
  { match: p => p.startsWith('/settings'), key: 'settings.title' },
  { match: p => p.startsWith('/fleet'), key: 'fleet.title' },
  { match: p => p.startsWith('/statistics'), key: 'statistics' },
  { match: p => p.startsWith('/shop'), key: 'shop.title' },
]

export const clientLoader = async (): Promise<any> => {
  try {
    const response = await getCurrentAdmin()
    return response
  } catch (error) {
    throw Response.redirect('/login')
  }
}

function TopbarTitle() {
  const { t } = useTranslation()
  const { pathname } = useLocation()
  const hit = TITLE_BY_PATH.find(row => row.match(pathname))
  return <h1 className="font-display truncate text-base font-semibold tracking-tight sm:text-lg">{t(hit?.key ?? 'dashboard')}</h1>
}

export default function DashboardLayout() {
  return (
    <SidebarProvider open onOpenChange={() => undefined} defaultOpen className="">
      <RouteGuard>
        <PageLoadOverlay />
        <TopLoadingBar />
        <DonationPopup />
        <div className="command-shell flex w-full min-h-svh flex-col lg:flex-row">
          <AppSidebar />
          <SidebarInset className="command-viewport min-w-0 flex-1 scroll-smooth">
            <TopbarAd />
            <VersionUpdateBanner />
            <header className="command-deck sticky top-0 z-20 px-2 py-2 sm:px-4 sm:py-2.5">
              <div className="command-deck__frame gap-2 sm:gap-3">
                <div className="flex min-w-0 items-center gap-2">
                  <SidebarTrigger className="lg:hidden" />
                  <div className="min-w-0">
                    <TopbarTitle />
                    <p className="text-muted-foreground hidden truncate text-[11px] tracking-wide sm:block">Operations console</p>
                  </div>
                </div>
                <QuestSearch compact className="max-w-xl flex-1" />
                <div className="flex shrink-0 items-center gap-1 sm:gap-1.5">
                  <CopilotLauncher />
                  <div className="bg-border/70 mx-0.5 hidden h-5 w-px sm:block" aria-hidden="true" />
                  <Language variant="header" />
                  <ThemeToggle variant="header" />
                  <span
                    className="ms-0.5 inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-[10px] font-semibold tracking-wide text-emerald-400 uppercase"
                    title="Live uplink"
                  >
                    <span className="online-beacon" />
                    Live
                  </span>
                </div>
              </div>
            </header>
            <div className="command-stage flex min-h-0 w-full flex-1 flex-col justify-between gap-y-3 sm:gap-y-4">
              <div className="command-stage__scan" aria-hidden="true" />
              <PageTransition duration={200} className="relative z-10 flex min-h-0 flex-1 flex-col">
                <Outlet />
              </PageTransition>
              <Footer />
            </div>
          </SidebarInset>
        </div>
      </RouteGuard>
    </SidebarProvider>
  )
}
