import PageHeader from '@/components/layout/page-header'
import PageTransition from '@/components/layout/page-transition'
import { SectorTabBar, type SectorTab } from '@/components/layout/sector-tab-bar'
import { useAdmin } from '@/hooks/use-admin'
import { getDocsUrl } from '@/utils/docs-url'
import { hasPermission } from '@/utils/rbac'
import { Cpu, Share2, Plus, Logs, Network } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router'

const tabs: SectorTab[] = [
  { id: 'nodes.title', label: 'nodes.title', icon: Share2, url: '/nodes' },
  { id: 'core', label: 'core', mobileLabel: 'settings.cores.title', icon: Cpu, url: '/nodes/cores' },
  { id: 'nodes.wireguard.title', label: 'nodes.wireguard.title', icon: Network, url: '/nodes/wireguard' },
  { id: 'nodes.logs.title', label: 'nodes.logs.title', icon: Logs, url: '/nodes/logs' },
]

const Settings = () => {
  const location = useLocation()
  const navigate = useNavigate()
  const { admin } = useAdmin()
  const canReadNodes = hasPermission(admin, 'nodes', 'read')
  const canCreateNodes = hasPermission(admin, 'nodes', 'create')
  const canReadCores = hasPermission(admin, 'cores', 'read')
  const canCreateCores = hasPermission(admin, 'cores', 'create')
  const canReadNodeLogs = hasPermission(admin, 'nodes', 'logs')
  const visibleTabs = tabs.filter(tab => {
    if (tab.url === '/nodes') return canReadNodes
    if (tab.url === '/nodes/cores') return canReadCores
    if (tab.url === '/nodes/wireguard') return canReadCores
    if (tab.url === '/nodes/logs') return canReadNodeLogs
    return false
  })
  const [activeTab, setActiveTab] = useState<string>(tabs[0].id)
  const isCoreEditorPage = /^\/nodes\/cores\/[^/]+$/.test(location.pathname)

  useEffect(() => {
    if (location.pathname.startsWith('/nodes/cores')) {
      setActiveTab('core')
      return
    }
    const currentTab = tabs.find(tab => location.pathname === tab.url)
    if (currentTab) {
      setActiveTab(currentTab.id)
    }
  }, [location.pathname])

  useEffect(() => {
    if (isCoreEditorPage || visibleTabs.length === 0) return
    const currentTab = visibleTabs.find(tab => location.pathname === tab.url)
    if (!currentTab) {
      navigate(visibleTabs[0].url, { replace: true })
    }
  }, [isCoreEditorPage, location.pathname, navigate, visibleTabs])

  const getPageHeaderProps = () => {
    if (location.pathname.startsWith('/nodes/cores')) {
      return {
        title: 'settings.cores.title',
        description: 'settings.cores.description',
        buttonIcon: canCreateCores ? Plus : undefined,
        buttonText: canCreateCores ? 'settings.cores.addCore' : undefined,
        onButtonClick: canCreateCores
          ? () => {
              navigate('/nodes/cores/new')
            }
          : undefined,
      }
    }
    if (location.pathname === '/nodes/wireguard') {
      return {
        title: 'nodes.wireguard.title',
        description: 'nodes.wireguard.description',
        buttonIcon: undefined,
        buttonText: undefined,
        onButtonClick: undefined,
      }
    }
    if (location.pathname === '/nodes/logs') {
      return {
        title: 'nodes.logs.title',
        description: 'nodes.logs.description',
        buttonIcon: undefined,
        buttonText: undefined,
        onButtonClick: undefined,
      }
    }
    return {
      title: 'nodes.title',
      description: 'manageNodes',
      buttonIcon: canCreateNodes ? Plus : undefined,
      buttonText: canCreateNodes ? 'nodes.addNode' : undefined,
      onButtonClick: canCreateNodes
        ? () => {
            const event = new CustomEvent('openNodeDialog')
            window.dispatchEvent(event)
          }
        : undefined,
    }
  }

  return (
    <div className="flex min-h-0 w-full flex-1 flex-col items-start gap-0">
      {!isCoreEditorPage && (
        <PageTransition isContentTransition={true}>
          <PageHeader {...getPageHeaderProps()} tutorialUrl={getDocsUrl(location.pathname)} />
        </PageTransition>
      )}
      <div className="flex min-h-0 w-full flex-1 flex-col">
        {!isCoreEditorPage && <SectorTabBar tabs={visibleTabs} activeId={activeTab} sector="Node grid" index="02" onSelect={tab => navigate(tab.url)} />}
        <PageTransition isContentTransition={true} className="flex min-h-0 flex-1 flex-col">
          <Outlet />
        </PageTransition>
      </div>
    </div>
  )
}

export default Settings
