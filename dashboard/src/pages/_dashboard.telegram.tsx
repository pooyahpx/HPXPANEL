import PageHeader from '@/components/layout/page-header'
import { TelegramBotHub } from '@/features/telegram-bot/telegram-bot-hub'
import { useAdmin } from '@/hooks/use-admin'
import { hasPermission } from '@/utils/rbac'
import { Navigate } from 'react-router'

export default function TelegramBotPage() {
  const { admin } = useAdmin()
  const canManage = hasPermission(admin, 'settings', 'read') && hasPermission(admin, 'settings', 'update')

  if (!canManage) {
    return <Navigate to="/" replace />
  }

  return (
    <div className="flex w-full flex-col">
      <PageHeader
        title="telegramBot.title"
        description="telegramBot.description"
        index="TG"
        sectorLabel="Messaging"
      />
      <TelegramBotHub />
    </div>
  )
}
