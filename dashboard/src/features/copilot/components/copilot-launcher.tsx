import { Button } from '@/components/ui/button'
import { CopilotSheet } from '@/features/copilot/components/copilot-sheet'
import { getCopilotStatus, getCopilotStatusQueryKey } from '@/service/api/copilot'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Sparkles } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

export function CopilotLauncher() {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()
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

  const onConfigured = () => {
    void queryClient.invalidateQueries({ queryKey: getCopilotStatusQueryKey() })
  }

  return (
    <>
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="command-copilot border-border/50 bg-background/80 hover:bg-accent/60 h-9 w-9 shrink-0 cursor-pointer gap-0 rounded-xl px-0 shadow-none sm:h-8 sm:w-auto sm:gap-2 sm:px-2.5"
        onClick={() => setOpen(true)}
        title={configured ? t('copilot.title') : t('copilot.notConfigured')}
        aria-label={t('copilot.title')}
      >
        <Sparkles className="h-4 w-4" />
        <span className="hidden sm:inline">{t('copilot.title')}</span>
      </Button>
      <CopilotSheet
        open={open}
        onOpenChange={setOpen}
        configured={configured}
        status={status}
        onConfigured={onConfigured}
      />
    </>
  )
}
