import PageHeader from '@/components/layout/page-header'
import { type UseEditFormValues, type UseFormValues, getDefaultUserForm } from '@/features/users/forms/user-form'
import UsersTable from '@/features/users/components/users-table'
import UsersStatistics from '@/features/users/components/users-statistics'
import { Plus } from 'lucide-react'
import UserModal from '@/features/users/dialogs/user-modal'
import { useAdmin } from '@/hooks/use-admin'
import { hasPermission } from '@/utils/rbac'
import { useState } from 'react'
import { useForm } from 'react-hook-form'

const Users = () => {
  const { admin } = useAdmin()
  const canCreateUsers = hasPermission(admin, 'users', 'create')
  const [isUserModalOpen, setUserModalOpen] = useState(false)
  const userForm = useForm<UseFormValues | UseEditFormValues>({
    defaultValues: getDefaultUserForm,
  })

  const handleCreateUser = () => {
    if (!canCreateUsers) return
    userForm.reset()
    setUserModalOpen(true)
  }

  return (
    <div className="flex w-full flex-col items-start">
      <div className="animate-fade-in w-full transform-gpu" style={{ animationDuration: '400ms' }}>
        <PageHeader
          title="users"
          description="manageAccounts"
          buttonIcon={canCreateUsers ? Plus : undefined}
          buttonText={canCreateUsers ? 'createUser' : undefined}
          onButtonClick={canCreateUsers ? handleCreateUser : undefined}
        />
      </div>

      <div className="mx-auto w-full max-w-[1680px] space-y-5 px-4 py-5 md:px-6 md:py-7">
        <div className="animate-slide-up transform-gpu" style={{ animationDuration: '500ms', animationDelay: '100ms', animationFillMode: 'both' }}>
          <UsersStatistics />
        </div>

        <div className="command-surface animate-slide-up transform-gpu" style={{ animationDuration: '500ms', animationDelay: '250ms', animationFillMode: 'both' }}>
          <div className="border-border flex items-center justify-between gap-4 border-b px-4 py-3">
            <div>
              <p className="text-primary font-mono text-[10px] font-bold tracking-[0.14em] uppercase">Identity matrix</p>
              <p className="text-muted-foreground text-xs">Live accounts, traffic and connection state</p>
            </div>
            <div className="hidden items-center gap-2 sm:flex">
              <span className="online-beacon" />
              <span className="font-mono text-[10px] font-bold tracking-[0.12em] uppercase">Realtime sync</span>
            </div>
          </div>
          <div className="p-3 sm:p-4">
            <UsersTable />
          </div>
        </div>
      </div>

      {canCreateUsers && <UserModal isDialogOpen={isUserModalOpen} onOpenChange={setUserModalOpen} form={userForm} editingUser={false} />}
    </div>
  )
}

export default Users
