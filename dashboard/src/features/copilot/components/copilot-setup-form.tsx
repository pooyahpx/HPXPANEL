import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { PasswordInput } from '@/components/ui/password-input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import {
  getCopilotStatusQueryKey,
  updateCopilotSettings,
  type CopilotSettingsUpdate,
  type CopilotStatusResponse,
} from '@/service/api/copilot'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, ExternalLink, Loader2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'

const GROQ_API_KEYS_URL = 'https://console.groq.com/keys'

const PROVIDERS = ['groq', 'openai', 'openrouter', 'ollama'] as const
const DEFAULT_MODELS: Record<(typeof PROVIDERS)[number], string> = {
  groq: 'openai/gpt-oss-20b',
  openai: 'gpt-4o-mini',
  openrouter: 'google/gemma-2-9b-it:free',
  ollama: 'llama3.2',
}

type CopilotSetupFormProps = {
  status?: CopilotStatusResponse
  onConfigured?: () => void
}

export function CopilotSetupForm({ status, onConfigured }: CopilotSetupFormProps) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [provider, setProvider] = useState<(typeof PROVIDERS)[number]>('groq')
  const [apiKey, setApiKey] = useState('')
  const [model, setModel] = useState(DEFAULT_MODELS.groq)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (!status) return
    if (PROVIDERS.includes(status.provider as (typeof PROVIDERS)[number])) {
      setProvider(status.provider as (typeof PROVIDERS)[number])
    }
    if (status.model) setModel(status.model)
  }, [status])

  const mutation = useMutation({
    mutationFn: (payload: CopilotSettingsUpdate) => updateCopilotSettings(payload),
    onSuccess: async data => {
      setError(null)
      setSaved(true)
      setApiKey('')
      await queryClient.invalidateQueries({ queryKey: getCopilotStatusQueryKey() })
      onConfigured?.()
      if (data.configured) {
        setTimeout(() => setSaved(false), 4000)
      }
    },
    onError: (e: unknown) => {
      const detail =
        (e as { data?: { detail?: string } })?.data?.detail ||
        (e as Error)?.message ||
        t('copilot.setupSaveError')
      setError(String(detail))
    },
  })

  const onProviderChange = (value: string) => {
    const next = value as (typeof PROVIDERS)[number]
    setProvider(next)
    setModel(DEFAULT_MODELS[next])
    setSaved(false)
  }

  const onSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    setError(null)
    const payload: CopilotSettingsUpdate = {
      enabled: true,
      provider,
      model: model.trim() || undefined,
    }
    if (apiKey.trim()) {
      payload.api_key = apiKey.trim()
    } else if (!status?.configured && provider !== 'ollama') {
      setError(t('copilot.setupApiKeyRequired'))
      return
    }
    mutation.mutate(payload)
  }

  const needsApiKey = provider !== 'ollama'

  return (
    <form onSubmit={onSubmit} className="bg-muted/60 space-y-3 rounded-lg border p-3 text-sm">
      <div>
        <p className="font-medium">{t('copilot.setupTitle')}</p>
        <p className="text-muted-foreground mt-1 text-xs leading-relaxed">{t('copilot.setupIntroPanel')}</p>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="copilot-provider" className="text-xs">
          {t('copilot.setupProvider')}
        </Label>
        <Select value={provider} onValueChange={onProviderChange}>
          <SelectTrigger id="copilot-provider" className="h-9">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {PROVIDERS.map(item => (
              <SelectItem key={item} value={item}>
                {t(`copilot.providers.${item}`)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {needsApiKey && (
        <div className="space-y-1.5">
          <div className="flex items-center justify-between gap-2">
            <Label htmlFor="copilot-api-key" className="text-xs">
              {t('copilot.setupApiKey')}
            </Label>
            {provider === 'groq' && (
              <a
                href={GROQ_API_KEYS_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary inline-flex items-center gap-1 text-[11px] font-medium hover:underline"
              >
                {t('copilot.getApiKey')}
                <ExternalLink className="h-3 w-3 shrink-0" />
              </a>
            )}
          </div>
          <PasswordInput
            id="copilot-api-key"
            value={apiKey}
            onChange={e => setApiKey(e.target.value)}
            placeholder={
              status?.api_key_masked
                ? t('copilot.setupApiKeyKeep', { masked: status.api_key_masked })
                : t('copilot.setupApiKeyPlaceholder')
            }
            className="h-9 font-mono text-xs"
            autoComplete="off"
          />
        </div>
      )}

      <div className="space-y-1.5">
        <Label htmlFor="copilot-model" className="text-xs">
          {t('copilot.setupModel')}
        </Label>
        <Input
          id="copilot-model"
          value={model}
          onChange={e => setModel(e.target.value)}
          className="h-9 font-mono text-xs"
          dir="ltr"
        />
      </div>

      {error && <p className="text-destructive text-xs">{error}</p>}
      {saved && (
        <p className="text-primary flex items-center gap-1.5 text-xs">
          <CheckCircle2 className="h-3.5 w-3.5" />
          {t('copilot.setupSaved')}
        </p>
      )}

      <Button type="submit" size="sm" className="w-full" disabled={mutation.isPending}>
        {mutation.isPending ? (
          <>
            <Loader2 className="me-2 h-4 w-4 animate-spin" />
            {t('copilot.setupSaving')}
          </>
        ) : (
          t('copilot.setupSave')
        )}
      </Button>

      <p className="text-muted-foreground text-[11px] leading-relaxed">{t('copilot.setupNoRestart')}</p>
    </form>
  )
}
