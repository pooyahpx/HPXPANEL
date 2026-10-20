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
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar'
import { getCurrentAdmin } from '@/service/api'
import { Outlet } from 'react-router'
import TopbarAd from '@/components/common/topbar-ad'
import { CopilotLauncher } from '@/features/copilot/components/copilot-launcher'
import { Activity } from 'lucide-react'

export const clientLoader = async (): Promise<any> => {
  try {
    const response = await getCurrentAdmin()
    return response
  } catch (error) {
    throw Response.redirect('/login')
  }
}

export default function DashboardLayout() {
  return (
    <SidebarProvider defaultOpen={false} className="">
      <RouteGuard>
        <PageLoadOverlay />
        <TopLoadingBar />
        <DonationPopup />
        <div className="command-shell flex w-full flex-col lg:flex-row">
          <AppSidebar />
          <SidebarInset className="command-viewport scroll-smooth">
            <TopbarAd />
            <VersionUpdateBanner />
            <header className="command-deck sticky top-0 z-20 px-2 py-2 sm:px-4 sm:py-3">
              <div className="command-deck__frame">
                <div className="hidden min-w-0 items-center gap-2.5 lg:flex">
                  <div className="command-deck__mark" aria-hidden="true">
                    <Activity className="h-4 w-4" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-foreground truncate text-sm font-semibold tracking-tight">HPXPANEL</p>
                    <p className="text-muted-foreground truncate text-[11px]">Operations console</p>
                  </div>
                </div>
                <QuestSearch compact className="max-w-2xl flex-1" />
                <div className="flex shrink-0 items-center gap-1 sm:gap-1.5">
                  <CopilotLauncher />
                  <div className="bg-border/70 mx-0.5 hidden h-5 w-px sm:block" aria-hidden="true" />
                  <div className="hidden items-center gap-1 sm:flex">
                    <Language />
                    <ThemeToggle />
                  </div>
                  <span
                    className="ms-0.5 hidden items-center gap-1.5 rounded-full border border-emerald-500/25 bg-emerald-500/10 px-2 py-1 text-[10px] font-semibold tracking-wide text-emerald-400 uppercase md:inline-flex"
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
              <PageTransition duration={220} className="relative z-10 flex min-h-0 flex-1 flex-col">
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
