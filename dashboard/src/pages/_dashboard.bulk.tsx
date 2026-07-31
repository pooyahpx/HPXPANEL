import PageHeader from '@/components/layout/page-header'
import { SectorTabBar } from '@/components/layout/sector-tab-bar'
import { useAdmin } from '@/hooks/use-admin'
import PageTransition from '@/components/layout/page-transition'
import { getDocsUrl } from '@/utils/docs-url'
import { ArrowUpDown, Calendar, Lock, Group, UserPlus } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router'
import { canReadResourcePage, hasPermission, hasScopeAll } from '@/utils/rbac'

const allTabs = [
  { id: 'create', label: 'bulk.createUsers', icon: UserPlus, url: '/bulk' },
  { id: 'groups', label: 'bulk.groups', icon: Group, url: '/bulk/groups' },
  { id: 'expire', label: 'bulk.expireDate', icon: Calendar, url: '/bulk/expire' },
  { id: 'data', label: 'bulk.dataLimit', icon: ArrowUpDown, url: '/bulk/data' },
  { id: 'proxy', label: 'bulk.proxySettings', icon: Lock, url: '/bulk/proxy' },
]

const BulkPage = () => {
  const { admin } = useAdmin()
  const canCreateUsers = hasPermission(admin, 'users', 'create')
  const canReadUserTemplates = canReadResourcePage(admin, 'templates')
  const canBulkUpdate = hasScopeAll(admin, 'users', 'update')
  const tabs = allTabs.filter(tab => (tab.id === 'create' ? canCreateUsers && canReadUserTemplates : canBulkUpdate))
  const navigate = useNavigate()
  const location = useLocation()
  const [activeTab, setActiveTab] = useState(allTabs[0].id)

  useEffect(() => {
    if (tabs.length === 0) {
      navigate('/settings/theme', { replace: true })
      return
    }
    const currentTab = tabs.find(tab => {
      if (tab.id === 'create' && location.pathname === '/bulk/create') {
        return true
      }
      return location.pathname === tab.url
    })
    if (currentTab) {
      setActiveTab(currentTab.id)
      return
    }

    // Keep non-sudo admins on the only allowed bulk page.
    setActiveTab(tabs[0].id)
    navigate(tabs[0].url, { replace: true })
  }, [location.pathname, navigate, tabs])

  if (tabs.length === 0) return null

  const getPageHeaderProps = () => {
    const pathToHeader: Record<string, { title: string; description: string }> = {
      '/bulk': { title: 'bulk.createUsers', description: 'bulk.createUsersDesc' },
      '/bulk/create': { title: 'bulk.createUsers', description: 'bulk.createUsersDesc' },
      '/bulk/groups': { title: 'bulk.groups', description: 'bulk.groupsDesc' },
      '/bulk/expire': { title: 'bulk.expireDate', description: 'bulk.expireDateDesc' },
      '/bulk/data': { title: 'bulk.dataLimit', description: 'bulk.dataLimitDesc' },
      '/bulk/proxy': { title: 'bulk.proxySettings', description: 'bulk.proxySettingsDesc' },
    }

    const header = pathToHeader[location.pathname] || pathToHeader['/bulk']
    return {
      title: header.title,
      description: header.description,
    }
  }

  return (
    <div className="flex w-full flex-col items-start gap-0">
      <PageTransition isContentTransition={true}>
        <PageHeader {...getPageHeaderProps()} tutorialUrl={getDocsUrl(location.pathname)} />
      </PageTransition>
      <div className="w-full">
        <SectorTabBar tabs={tabs} activeId={activeTab} sector="Batch ops" index="03" onSelect={tab => navigate(tab.url)} />
        <div className="px-4 py-6 lg:px-6">
          <PageTransition isContentTransition={true}>
            <Outlet />
          </PageTransition>
        </div>
      </div>
    </div>
  )
}

export default BulkPage
