import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import useDirDetection from '@/hooks/use-dir-detection'
import { cn } from '@/lib/utils'
import { fetcher } from '@/service/http'
import { hostFormDefaultValues, type HostFormValues } from '@/features/hosts/forms/host-form'
import { Shield, Sparkles } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@tanstack/react-query'

export interface HostStealthPreset {
  id: string
  title: string
  title_fa: string
  intent: string
  stack: string
  description: string
  description_fa: string
  host_patch: Partial<HostFormValues> & Record<string, unknown>
}

interface HostStealthPresetsResponse {
  presets: HostStealthPreset[]
  total: number
}

async function fetchStealthPresets(intent?: string): Promise<HostStealthPresetsResponse> {
  const qs = intent && intent !== 'all' ? `?intent=${encodeURIComponent(intent)}` : ''
  return fetcher(`/api/host/stealth-presets${qs}`, { method: 'GET' })
}

export function applyHostStealthPreset(preset: HostStealthPreset): HostFormValues {
  const patch = preset.host_patch || {}
  return {
    ...hostFormDefaultValues,
    ...patch,
    remark: typeof patch.remark === 'string' ? patch.remark : hostFormDefaultValues.remark,
    address: Array.isArray(patch.address) ? (patch.address as string[]) : hostFormDefaultValues.address,
    inbound_tag: typeof patch.inbound_tag === 'string' ? patch.inbound_tag : hostFormDefaultValues.inbound_tag,
    status: Array.isArray(patch.status) ? (patch.status as HostFormValues['status']) : hostFormDefaultValues.status,
    security: (patch.security as HostFormValues['security']) || hostFormDefaultValues.security,
    allowinsecure: typeof patch.allowinsecure === 'boolean' ? patch.allowinsecure : hostFormDefaultValues.allowinsecure,
    is_disabled: false,
    random_user_agent: false,
    use_sni_as_host: false,
    priority: 0,
    fingerprint: typeof patch.fingerprint === 'string' ? patch.fingerprint : hostFormDefaultValues.fingerprint,
    sni: Array.isArray(patch.sni) ? (patch.sni as string[]) : hostFormDefaultValues.sni,
    host: Array.isArray(patch.host) ? (patch.host as string[]) : hostFormDefaultValues.host,
    path: typeof patch.path === 'string' ? patch.path : hostFormDefaultValues.path,
    alpn: Array.isArray(patch.alpn) ? (patch.alpn as string[]) : hostFormDefaultValues.alpn,
    fragment_settings: (patch.fragment_settings as HostFormValues['fragment_settings']) ?? undefined,
    noise_settings: (patch.noise_settings as HostFormValues['noise_settings']) ?? undefined,
    mux_settings: (patch.mux_settings as HostFormValues['mux_settings']) ?? hostFormDefaultValues.mux_settings,
    http_headers: (patch.http_headers as Record<string, string>) || {},
  }
}

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  onApply: (values: HostFormValues, preset: HostStealthPreset) => void
}

export default function HostStealthPresetWizard({ open, onOpenChange, onApply }: Props) {
  const { t, i18n } = useTranslation()
  const dir = useDirDetection()
  const fa = i18n.language?.startsWith('fa')
  const [intent, setIntent] = useState<string>('all')

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['host-stealth-presets', intent],
    queryFn: () => fetchStealthPresets(intent === 'all' ? undefined : intent),
    enabled: open,
  })

  useEffect(() => {
    if (open) void refetch()
  }, [open, refetch])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent dir={dir} className={cn('max-h-[90vh] overflow-y-auto sm:max-w-xl', dir === 'rtl' && 'text-right')}>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Shield className="size-4" />
            {t('hostStealthPresets.title', { defaultValue: 'HPX Stealth presets' })}
          </DialogTitle>
          <DialogDescription>
            {t('hostStealthPresets.description', {
              defaultValue: 'One-page Reality / Hysteria2 / fragment presets. Pick an intent, apply, then finish inbound tag in the host form.',
            })}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div className="space-y-1.5">
            <p className="text-sm font-medium">{t('hostStealthPresets.intent', { defaultValue: 'Intent' })}</p>
            <Select value={intent} onValueChange={setIntent}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t('hostStealthPresets.all', { defaultValue: 'All' })}</SelectItem>
                <SelectItem value="mobile">{t('hostStealthPresets.mobile', { defaultValue: 'Mobile' })}</SelectItem>
                <SelectItem value="hard">{t('hostStealthPresets.hard', { defaultValue: 'Hard DPI' })}</SelectItem>
                <SelectItem value="fast">{t('hostStealthPresets.fast', { defaultValue: 'Fast' })}</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {isLoading && <p className="text-muted-foreground text-sm">{t('loading', { defaultValue: 'Loading…' })}</p>}

          <div className="space-y-2">
            {(data?.presets ?? []).map(preset => (
              <button
                key={preset.id}
                type="button"
                className="hover:border-primary/40 w-full rounded-lg border p-3 text-start transition-colors"
                onClick={() => {
                  onApply(applyHostStealthPreset(preset), preset)
                  onOpenChange(false)
                }}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="text-sm font-medium">{fa ? preset.title_fa : preset.title}</span>
                  <div className="flex gap-1">
                    <Badge variant="outline" className="text-[10px] uppercase">
                      {preset.intent}
                    </Badge>
                    <Badge variant="secondary" className="text-[10px] uppercase">
                      {preset.stack}
                    </Badge>
                  </div>
                </div>
                <p className="text-muted-foreground mt-1 text-xs leading-relaxed">
                  {fa ? preset.description_fa : preset.description}
                </p>
              </button>
            ))}
          </div>

          <div className="flex justify-end gap-2 pt-1">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              {t('cancel', { defaultValue: 'Cancel' })}
            </Button>
            <Button type="button" variant="secondary" disabled className="gap-1.5">
              <Sparkles className="size-3.5" />
              {t('hostStealthPresets.hint', { defaultValue: 'Click a preset to apply' })}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
