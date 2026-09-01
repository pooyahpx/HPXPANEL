import { Button } from '@/components/ui/button'
import { CopilotSheet } from '@/features/copilot/components/copilot-sheet'
import { getCopilotStatus, getCopilotStatusQueryKey } from '@/service/api/copilot'
import { useQuery } from '@tanstack/react-query'
import { Sparkles } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

export function CopilotLauncher() {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const { data: status } = useQuery({
    queryKey: getCopilotStatusQueryKey(),
    queryFn: getCopilotStatus,
    staleTime: 60_000,
    retry: false,
  })

  const configured = status?.configured ?? false

  return (
    <>
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="command-copilot gap-2"
        onClick={() => setOpen(true)}
        title={t('copilot.title')}
      >
        <Sparkles className="h-4 w-4" />
        <span className="hidden md:inline">{t('copilot.title')}</span>
      </Button>
      <CopilotSheet open={open} onOpenChange={setOpen} configured={configured} />
    </>
  )
}
