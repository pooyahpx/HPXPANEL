import { Footer } from '@/components/layout/footer'
import { AppSidebar } from '@/components/layout/sidebar'
import { PageLoadOverlay } from '@/components/layout/page-load-overlay'
import PageTransition from '@/components/layout/page-transition'
import { QuestSearch } from '@/components/layout/quest-search'
import RouteGuard from '@/components/layout/route-guard'
import { TopLoadingBar } from '@/components/layout/top-loading-bar'
import { VersionUpdateBanner } from '@/components/layout/version-update-banner'
import DonationPopup from '@/components/common/donation-popup'
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar'
import { getCurrentAdmin } from '@/service/api'
import { Outlet } from 'react-router'
import TopbarAd from '@/components/common/topbar-ad'
import { CopilotLauncher } from '@/features/copilot/components/copilot-launcher'
import { Activity, Command, Radio } from 'lucide-react'

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
            <header className="command-deck sticky top-0 z-20 px-3 py-3 md:px-5">
              <div className="command-deck__frame">
                <div className="hidden min-w-44 items-center gap-3 lg:flex">
                  <div className="command-deck__mark">
                    <Command className="h-4 w-4" />
                  </div>
                  <div>
                    <p className="text-primary font-mono text-[10px] font-bold tracking-[0.16em] uppercase">HPX // Command deck</p>
                    <p className="text-muted-foreground text-xs">Global operations console</p>
                  </div>
                </div>
                <QuestSearch compact className="max-w-2xl flex-1" />
                <div className="flex shrink-0 items-center gap-2">
                  <CopilotLauncher />
                  <span className="command-signal hidden sm:grid" aria-hidden="true">
                    <Radio className="h-3.5 w-3.5" />
                  </span>
                  <span className="hidden font-mono text-[10px] font-bold tracking-[0.12em] uppercase sm:inline">Live uplink</span>
                  <Activity className="hidden h-4 w-4 text-emerald-400 sm:block" />
                </div>
              </div>
            </header>
            <div className="command-stage flex min-h-0 w-full flex-1 flex-col justify-between gap-y-4">
              <div className="command-stage__scan" aria-hidden="true" />
              <PageTransition duration={250} className="relative z-10 flex min-h-0 flex-1 flex-col">
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
