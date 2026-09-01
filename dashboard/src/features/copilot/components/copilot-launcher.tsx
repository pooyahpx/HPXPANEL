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

  if (status && status.enabled === false) {
    return null
  }

  const configured = status?.configured ?? false

  return (
    <>
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="command-copilot shrink-0 gap-2"
        onClick={() => setOpen(true)}
        title={configured ? t('copilot.title') : t('copilot.notConfigured')}
      >
        <Sparkles className="h-4 w-4" />
        <span className="max-[420px]:sr-only sm:inline">{t('copilot.title')}</span>
      </Button>
      <CopilotSheet open={open} onOpenChange={setOpen} configured={configured} />
    </>
  )
}
