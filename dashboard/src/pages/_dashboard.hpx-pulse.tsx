import PageHeader from '@/components/layout/page-header'
import PageTransition from '@/components/layout/page-transition'
import HpxPulseList from '@/features/hpx-pulse/components/hpx-pulse-list'
import { useAdmin } from '@/hooks/use-admin'
import { hasPermission } from '@/utils/rbac'
import { Plus } from 'lucide-react'

export default function HpxPulsePage() {
  const { admin } = useAdmin()
  const canCreate = hasPermission(admin, 'hpx_pulse', 'create')

  return (
    <div className="flex min-h-0 w-full flex-1 flex-col items-start gap-0">
      <PageTransition isContentTransition>
        <PageHeader
          title="hpxPulse.title"
          description="hpxPulse.description"
          buttonIcon={canCreate ? Plus : undefined}
          buttonText={canCreate ? 'hpxPulse.add' : undefined}
          onButtonClick={
            canCreate
              ? () => {
                  window.dispatchEvent(new CustomEvent('openHpxPulseDialog'))
                }
              : undefined
          }
        />
      </PageTransition>
      <PageTransition isContentTransition className="flex min-h-0 flex-1 flex-col">
        <HpxPulseList />
      </PageTransition>
    </div>
  )
}
