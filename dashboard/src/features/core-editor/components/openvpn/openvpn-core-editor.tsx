import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
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

  return (
    <div className="space-y-6">
      <Alert>
        <AlertTitle>{t('coreEditor.openvpn.title')}</AlertTitle>
        <AlertDescription>
          <p>{t('coreEditor.openvpn.description')}</p>
          <p className="text-muted-foreground mt-1 font-mono text-xs">{t('coreEditor.openvpn.ports')}</p>
        </AlertDescription>
      </Alert>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="openvpn-inbound-tag">{t('coreEditor.openvpn.fields.inbound_tag')}</Label>
          <Input id="openvpn-inbound-tag" value={draft.inbound_tag} onChange={event => updateString('inbound_tag', event.target.value)} dir="ltr" />
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
          <Label htmlFor="openvpn-proto">{t('coreEditor.openvpn.fields.proto')}</Label>
          <Input id="openvpn-proto" value={draft.proto} onChange={event => updateString('proto', event.target.value)} placeholder="udp" dir="ltr" />
        </div>
        <div className="space-y-2">
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
