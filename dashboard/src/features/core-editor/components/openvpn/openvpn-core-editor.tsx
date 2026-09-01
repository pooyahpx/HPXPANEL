import { OpenVPNCertHelp } from '@/features/core-editor/components/openvpn/openvpn-cert-help'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import {
  applyOpenVPNProtoPreset,
  OPENVPN_PROTO_PRESETS,
  resolveOpenVPNProtoPreset,
  type OpenVPNProtoPreset,
} from '@/features/core-editor/kit/openvpn-config'
import { useCoreEditorStore } from '@/features/core-editor/state/core-editor-store'
import { useTranslation } from 'react-i18next'

function SecretTextarea({
  id,
  label,
  value,
  placeholder,
  onChange,
}: {
  id: string
  label: string
  value: string
  placeholder: string
  onChange: (value: string) => void
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <Textarea id={id} value={value} onChange={event => onChange(event.target.value)} placeholder={placeholder} dir="ltr" className="min-h-28 font-mono text-xs" />
    </div>
  )
}

export function OpenVPNCoreEditor() {
  const { t } = useTranslation()
  const kind = useCoreEditorStore(s => s.kind)
  const draft = useCoreEditorStore(s => s.openvpnDraft)
  const updateOpenvpnDraft = useCoreEditorStore(s => s.updateOpenvpnDraft)

  if (kind !== 'openvpn' || !draft) return null

  const updateString = (field: keyof typeof draft, value: string) => {
    updateOpenvpnDraft(current => ({ ...current, [field]: value }))
  }

  const updateNumber = (field: keyof typeof draft, value: number) => {
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

  return (
    <div className="space-y-6">
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

      <div className="grid gap-4">
        <SecretTextarea
          id="openvpn-ca-cert"
          label={t('coreEditor.openvpn.fields.ca_cert')}
          value={draft.ca_cert}
          placeholder={t('coreEditor.openvpn.placeholders.ca_cert')}
          onChange={value => updateString('ca_cert', value)}
        />
        <SecretTextarea
          id="openvpn-server-cert"
          label={t('coreEditor.openvpn.fields.server_cert')}
          value={draft.server_cert}
          placeholder={t('coreEditor.openvpn.placeholders.server_cert')}
          onChange={value => updateString('server_cert', value)}
        />
        <SecretTextarea
          id="openvpn-server-key"
          label={t('coreEditor.openvpn.fields.server_key')}
          value={draft.server_key}
          placeholder={t('coreEditor.openvpn.placeholders.server_key')}
          onChange={value => updateString('server_key', value)}
        />
        <SecretTextarea
          id="openvpn-tls-crypt"
          label={t('coreEditor.openvpn.fields.tls_crypt_key')}
          value={draft.tls_crypt_key}
          placeholder={t('coreEditor.openvpn.placeholders.tls_crypt_key')}
          onChange={value => updateString('tls_crypt_key', value)}
        />
      </div>
    </div>
  )
}
