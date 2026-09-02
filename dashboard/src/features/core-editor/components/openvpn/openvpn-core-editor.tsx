import { OpenVPNCertHelp } from '@/features/core-editor/components/openvpn/openvpn-cert-help'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import {
  applyOpenVPNProtoPreset,
  OPENVPN_PROTO_PRESETS,
  resolveOpenVPNProtoPreset,
  type OpenVPNCoreConfig,
  type OpenVPNProtoPreset,
} from '@/features/core-editor/kit/openvpn-config'
import { useCoreEditorStore } from '@/features/core-editor/state/core-editor-store'
import { generateOpenVPNPki, type OpenVPNPkiBundle } from '@/service/api/openvpn'
import { Loader2, Sparkles, TriangleAlert } from 'lucide-react'
import { useCallback, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

type OpenVPNPkiField = 'ca_cert' | 'server_cert' | 'server_key' | 'tls_crypt_key'

function SecretTextarea({
  id,
  label,
  value,
  placeholder,
  onChange,
  onGenerate,
  generating,
}: {
  id: string
  label: string
  value: string
  placeholder: string
  onChange: (value: string) => void
  onGenerate: () => void
  generating: boolean
}) {
  const { t } = useTranslation()

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <Label htmlFor={id}>{label}</Label>
        <Button type="button" size="sm" variant="secondary" className="h-8 gap-1.5" onClick={onGenerate} disabled={generating}>
          {generating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
          {t('coreEditor.openvpn.autoGenerate')}
        </Button>
      </div>
      <Textarea id={id} value={value} onChange={event => onChange(event.target.value)} placeholder={placeholder} dir="ltr" className="min-h-28 font-mono text-xs" />
    </div>
  )
}

export function OpenVPNCoreEditor() {
  const { t } = useTranslation()
  const kind = useCoreEditorStore(s => s.kind)
  const draft = useCoreEditorStore(s => s.openvpnDraft)
  const updateOpenvpnDraft = useCoreEditorStore(s => s.updateOpenvpnDraft)
  const pkiBundleRef = useRef<OpenVPNPkiBundle | null>(null)
  const [generatingField, setGeneratingField] = useState<OpenVPNPkiField | 'all' | null>(null)

  const ensurePkiBundle = useCallback(async (force = false) => {
    if (!force && pkiBundleRef.current) return pkiBundleRef.current
    const bundle = await generateOpenVPNPki()
    pkiBundleRef.current = bundle
    return bundle
  }, [])

  const fillField = useCallback(
    async (field: OpenVPNPkiField, force = false) => {
      setGeneratingField(field)
      try {
        const bundle = await ensurePkiBundle(force)
        updateOpenvpnDraft(current => ({ ...current, [field]: bundle[field] }))
        toast.success(t('coreEditor.openvpn.autoGenerateSuccess', { field: t(`coreEditor.openvpn.fields.${field}`) }))
      } catch (error: unknown) {
        const detail = (error as { data?: { detail?: string } })?.data?.detail || (error as Error)?.message
        toast.error(detail ? String(detail) : t('coreEditor.openvpn.autoGenerateError'))
      } finally {
        setGeneratingField(null)
      }
    },
    [ensurePkiBundle, t, updateOpenvpnDraft],
  )

  const fillAllFields = useCallback(async () => {
    setGeneratingField('all')
    try {
      const bundle = await ensurePkiBundle(true)
      updateOpenvpnDraft(current => ({
        ...current,
        ca_cert: bundle.ca_cert,
        ca_key: bundle.ca_key,
        server_cert: bundle.server_cert,
        server_key: bundle.server_key,
        tls_crypt_key: bundle.tls_crypt_key,
      }))
      toast.success(t('coreEditor.openvpn.autoGenerateAllSuccess'))
    } catch (error: unknown) {
      const detail = (error as { data?: { detail?: string } })?.data?.detail || (error as Error)?.message
      toast.error(detail ? String(detail) : t('coreEditor.openvpn.autoGenerateError'))
    } finally {
      setGeneratingField(null)
    }
  }, [ensurePkiBundle, t, updateOpenvpnDraft])

  if (kind !== 'openvpn' || !draft) return null

  const updateString = (field: keyof OpenVPNCoreConfig, value: string) => {
    updateOpenvpnDraft(current => ({ ...current, [field]: value }))
  }

  const updateNumber = (field: keyof OpenVPNCoreConfig, value: number) => {
    updateOpenvpnDraft(current => ({ ...current, [field]: value }))
  }

  const updateLines = (field: 'dns' | 'push' | 'extra_server_directives', raw: string) => {
    updateOpenvpnDraft(current => ({
      ...current,
      [field]: raw
        .split('\n')
        .map(line => line.trim())
        .filter(Boolean),
    }))
  }

  const protoPreset = resolveOpenVPNProtoPreset(draft.proto, draft.port)
  const activePresetHint =
    protoPreset !== 'custom' ? t(OPENVPN_PROTO_PRESETS[protoPreset].hintKey) : t('coreEditor.openvpn.protoPresets.customHint')

  const onProtoPresetChange = (value: string) => {
    if (value === 'custom') return
    const next = applyOpenVPNProtoPreset(value as OpenVPNProtoPreset)
    updateOpenvpnDraft(current => ({ ...current, ...next }))
  }

  const isGenerating = generatingField !== null

  return (
    <div className="space-y-6">
      {draft.ca_cert?.trim() && !draft.ca_key?.trim() && (
        <Alert variant="destructive">
          <TriangleAlert className="h-4 w-4" />
          <AlertTitle>{t('coreEditor.openvpn.caKeyMissingTitle')}</AlertTitle>
          <AlertDescription>{t('coreEditor.openvpn.caKeyMissingWarning')}</AlertDescription>
        </Alert>
      )}
      <Alert>
        <AlertTitle>{t('coreEditor.openvpn.title')}</AlertTitle>
        <AlertDescription>
          <p>{t('coreEditor.openvpn.description')}</p>
        </AlertDescription>
      </Alert>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="openvpn-inbound-tag">{t('coreEditor.openvpn.fields.inbound_tag')}</Label>
          <Input id="openvpn-inbound-tag" value={draft.inbound_tag} onChange={event => updateString('inbound_tag', event.target.value)} dir="ltr" />
        </div>
        <div className="space-y-2">
          <Label htmlFor="openvpn-proto-preset">{t('coreEditor.openvpn.fields.proto')}</Label>
          <Select value={protoPreset === 'custom' ? '' : protoPreset} onValueChange={onProtoPresetChange}>
            <SelectTrigger id="openvpn-proto-preset" className="h-10 w-full min-w-0" dir="ltr">
              <SelectValue
                placeholder={
                  protoPreset === 'custom'
                    ? t('coreEditor.openvpn.protoPresets.custom', {
                        proto: draft.proto.toUpperCase(),
                        port: draft.port,
                      })
                    : t('coreEditor.openvpn.fields.proto')
                }
              />
            </SelectTrigger>
            <SelectContent>
              {(Object.keys(OPENVPN_PROTO_PRESETS) as OpenVPNProtoPreset[]).map(key => (
                <SelectItem key={key} value={key}>
                  {t(OPENVPN_PROTO_PRESETS[key].labelKey)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-muted-foreground text-xs">{activePresetHint}</p>
        </div>
        <div className="space-y-2">
          <Label htmlFor="openvpn-port">{t('coreEditor.openvpn.fields.port')}</Label>
          <Input
            id="openvpn-port"
            type="number"
            value={draft.port}
            onChange={event => updateNumber('port', Number(event.target.value) || 0)}
            dir="ltr"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="openvpn-proto">{t('coreEditor.openvpn.fields.protoValue')}</Label>
          <Input id="openvpn-proto" value={draft.proto} readOnly dir="ltr" className="bg-muted" />
        </div>
        <div className="space-y-2 md:col-span-2">
          <Label htmlFor="openvpn-subnet">{t('coreEditor.openvpn.fields.server_subnet')}</Label>
          <Input
            id="openvpn-subnet"
            value={draft.server_subnet}
            onChange={event => updateString('server_subnet', event.target.value)}
            placeholder="10.29.0.0/16"
            dir="ltr"
          />
        </div>
        <div className="space-y-2 md:col-span-2">
          <Label htmlFor="openvpn-dns">{t('coreEditor.openvpn.fields.dns')}</Label>
          <Textarea id="openvpn-dns" value={draft.dns.join('\n')} onChange={event => updateLines('dns', event.target.value)} dir="ltr" className="min-h-20 font-mono text-xs" />
          <p className="text-muted-foreground text-xs">{t('coreEditor.openvpn.onePerLine')}</p>
        </div>
        <div className="flex items-center justify-between rounded-md border p-3 md:col-span-2">
          <div>
            <p className="text-sm font-medium">{t('coreEditor.openvpn.fields.duplicate_cn')}</p>
            <p className="text-muted-foreground text-xs">{t('coreEditor.openvpn.duplicateCnHint')}</p>
          </div>
          <Switch checked={draft.duplicate_cn} onCheckedChange={checked => updateOpenvpnDraft(current => ({ ...current, duplicate_cn: checked }))} />
        </div>
      </div>

      <OpenVPNCertHelp />

      <div className="flex justify-end">
        <Button type="button" variant="default" className="gap-1.5" onClick={() => void fillAllFields()} disabled={isGenerating}>
          {generatingField === 'all' ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
          {t('coreEditor.openvpn.autoGenerateAll')}
        </Button>
      </div>

      <div className="grid gap-4">
        <SecretTextarea
          id="openvpn-ca-cert"
          label={t('coreEditor.openvpn.fields.ca_cert')}
          value={draft.ca_cert}
          placeholder={t('coreEditor.openvpn.placeholders.ca_cert')}
          onChange={value => updateString('ca_cert', value)}
          onGenerate={() => void fillField('ca_cert')}
          generating={generatingField === 'ca_cert' || generatingField === 'all'}
        />
        <SecretTextarea
          id="openvpn-server-cert"
          label={t('coreEditor.openvpn.fields.server_cert')}
          value={draft.server_cert}
          placeholder={t('coreEditor.openvpn.placeholders.server_cert')}
          onChange={value => updateString('server_cert', value)}
          onGenerate={() => void fillField('server_cert')}
          generating={generatingField === 'server_cert' || generatingField === 'all'}
        />
        <SecretTextarea
          id="openvpn-server-key"
          label={t('coreEditor.openvpn.fields.server_key')}
          value={draft.server_key}
          placeholder={t('coreEditor.openvpn.placeholders.server_key')}
          onChange={value => updateString('server_key', value)}
          onGenerate={() => void fillField('server_key')}
          generating={generatingField === 'server_key' || generatingField === 'all'}
        />
        <SecretTextarea
          id="openvpn-tls-crypt"
          label={t('coreEditor.openvpn.fields.tls_crypt_key')}
          value={draft.tls_crypt_key}
          placeholder={t('coreEditor.openvpn.placeholders.tls_crypt_key')}
          onChange={value => updateString('tls_crypt_key', value)}
          onGenerate={() => void fillField('tls_crypt_key')}
          generating={generatingField === 'tls_crypt_key' || generatingField === 'all'}
        />
      </div>
    </div>
  )
}
