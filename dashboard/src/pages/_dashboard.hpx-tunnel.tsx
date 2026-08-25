import PageHeader from '@/components/layout/page-header'
import PageTransition from '@/components/layout/page-transition'
import HpxTunnelsList from '@/features/hpx-tunnels/components/hpx-tunnels-list'
import { useAdmin } from '@/hooks/use-admin'
import { getDocsUrl } from '@/utils/docs-url'
import { hasPermission } from '@/utils/rbac'
import { Plus } from 'lucide-react'

export default function HpxTunnelPage() {
  const { admin } = useAdmin()
  const canCreate = hasPermission(admin, 'hpx_tunnels', 'create')

  return (
    <div className="flex min-h-0 w-full flex-1 flex-col items-start gap-0">
      <PageTransition isContentTransition>
        <PageHeader
          title="hpxTunnel.title"
          description="hpxTunnel.description"
          tutorialUrl={getDocsUrl('/hpx-tunnel')}
          buttonIcon={canCreate ? Plus : undefined}
          buttonText={canCreate ? 'hpxTunnel.addTunnel' : undefined}
          onButtonClick={
            canCreate
              ? () => {
                  window.dispatchEvent(new CustomEvent('openHpxTunnelDialog'))
                }
              : undefined
          }
        />
      </PageTransition>
      <PageTransition isContentTransition className="flex min-h-0 flex-1 flex-col">
        <HpxTunnelsList />
      </PageTransition>
    </div>
  )
}
