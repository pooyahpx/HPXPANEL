import PageHeader from '@/components/layout/page-header'
import ResourcePageShell from '@/components/layout/resource-page-shell'
import { Plus } from 'lucide-react'
import Groups from '@/features/groups/components/groups-list'
import { useAdmin } from '@/hooks/use-admin'
import { hasPermission } from '@/utils/rbac'
import { useState } from 'react'

export default function GroupsPage() {
  const { admin } = useAdmin()
  const canCreateGroups = hasPermission(admin, 'groups', 'create')
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const handleCreateGroup = () => {
    if (!canCreateGroups) return
    setIsDialogOpen(true)
  }

  return (
    <div className="flex w-full flex-col items-start">
      <div className="animate-fade-in w-full transform-gpu" style={{ animationDuration: '400ms' }}>
        <PageHeader
          title="groups"
          description="manageGroups"
          index="03"
          sectorLabel="Policy Clusters"
          buttonIcon={canCreateGroups ? Plus : undefined}
          buttonText={canCreateGroups ? 'createGroup' : undefined}
          onButtonClick={canCreateGroups ? handleCreateGroup : undefined}
        />
      </div>

      <ResourcePageShell sectorIndex="03-G" sectorLabel="Policy Clusters" description="Organized policy sets, allocation rules and membership control" stateLabel="Ready">
        <Groups isDialogOpen={isDialogOpen} onOpenChange={setIsDialogOpen} />
      </ResourcePageShell>
    </div>
  )
}
