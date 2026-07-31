import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { PasswordInput } from '@/components/ui/password-input'
import { Textarea } from '@/components/ui/textarea'
import { XrayAdvancedSection } from '@/features/core-editor/components/xray/xray-advanced-section'
import { useCoreEditorStore, type IpsecCoreSection } from '@/features/core-editor/state/core-editor-store'
import { cn } from '@/lib/utils'
import { Eye, EyeOff, ShieldCheck } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

type StringField = 'inbound_tag' | 'server_addr' | 'identity' | 'psk' | 'pool' | 'local_ip' | 'egress_interface' | 'ca_cert' | 'server_cert' | 'server_key'
type ArrayField = 'dns' | 'ike_proposals' | 'esp_proposals'

function SecretTextarea({ id, label, value, placeholder, onChange }: { id: string; label: string; value: string; placeholder: string; onChange: (value: string) => void }) {
  const { t } = useTranslation()
  const [revealed, setRevealed] = useState(false)

  return (
    <div className="space-y-2 sm:col-span-2">
      <div className="flex items-center justify-between gap-2">
        <Label htmlFor={id}>{label}</Label>
        <Button type="button" size="sm" variant="ghost" className="h-7 gap-1.5 px-2 text-xs" onClick={() => setRevealed(value => !value)} aria-controls={id} aria-pressed={revealed}>
          {revealed ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
          {revealed ? t('coreEditor.ipsec.hideSecret') : t('coreEditor.ipsec.showSecret')}
        </Button>
      </div>
      <Textarea
        id={id}
        rows={7}
        value={value}
        onChange={event => onChange(event.target.value)}
        placeholder={placeholder}
        autoComplete="off"
        autoCapitalize="off"
        spellCheck={false}
        dir="ltr"
        className={cn('resize-y font-mono text-xs', !revealed && '[-webkit-text-security:disc]')}
      />
    </div>
  )
}

export function IpsecCoreEditor() {
  const { t } = useTranslation()
  const kind = useCoreEditorStore(s => s.kind)
  const section = useCoreEditorStore(s => s.activeSection) as IpsecCoreSection
  const draft = useCoreEditorStore(s => s.ipsecDraft)
  const updateDraft = useCoreEditorStore(s => s.updateIpsecDraft)

  if ((kind !== 'ikev2' && kind !== 'l2tp') || !draft) return null
  if (section === 'advanced') return <XrayAdvancedSection />

  const updateString = (field: StringField, value: string) => updateDraft(current => ({ ...current, [field]: value }))
  const updateArray = (field: ArrayField, value: string) =>
    updateDraft(current => ({
      ...current,
      [field]: value
        .split('\n')
        .map(item => item.trim())
        .filter(Boolean),
    }))

  const textField = (field: StringField, options?: { secret?: boolean; span?: boolean }) => {
    const value = String(draft[field] ?? '')
    const label = t(`coreEditor.ipsec.fields.${field}`)
    const placeholder = t(`coreEditor.ipsec.placeholders.${field}`)
    return (
      <div className={cn('space-y-2', options?.span && 'sm:col-span-2')}>
        <Label htmlFor={`ipsec-${field}`}>{label}</Label>
        {options?.secret ? (
          <PasswordInput
            id={`ipsec-${field}`}
            value={value}
            onChange={event => updateString(field, event.target.value)}
            placeholder={placeholder}
            autoComplete="new-password"
            dir="ltr"
            className="font-mono text-xs"
          />
        ) : (
          <Input id={`ipsec-${field}`} value={value} onChange={event => updateString(field, event.target.value)} placeholder={placeholder} dir="ltr" />
        )}
      </div>
    )
  }

  const arrayField = (field: ArrayField) => (
    <div className="space-y-2">
      <Label htmlFor={`ipsec-${field}`}>{t(`coreEditor.ipsec.fields.${field}`)}</Label>
      <Textarea
        id={`ipsec-${field}`}
        rows={4}
        value={(draft[field] ?? []).join('\n')}
        onChange={event => updateArray(field, event.target.value)}
        placeholder={t(`coreEditor.ipsec.placeholders.${field}`)}
        spellCheck={false}
        dir="ltr"
        className="font-mono text-xs"
      />
      <p className="text-muted-foreground text-xs">{t('coreEditor.ipsec.onePerLine')}</p>
    </div>
  )

  return (
    <div className="space-y-5">
      <Alert>
        <ShieldCheck className="h-4 w-4" />
        <AlertTitle>{kind === 'ikev2' ? t('coreEditor.ipsec.ikev2Title') : t('coreEditor.ipsec.l2tpTitle')}</AlertTitle>
        <AlertDescription>
          <p>{kind === 'ikev2' ? t('coreEditor.ipsec.ikev2Description') : t('coreEditor.ipsec.l2tpDescription')}</p>
          <p className="mt-1 font-mono text-xs">{kind === 'ikev2' ? t('coreEditor.ipsec.ikev2Ports') : t('coreEditor.ipsec.l2tpPorts')}</p>
        </AlertDescription>
      </Alert>

      <div className="grid grid-cols-1 gap-x-4 gap-y-5 sm:grid-cols-2">
        {textField('inbound_tag')}
        {textField('server_addr')}
        {kind === 'ikev2' ? textField('identity') : textField('local_ip')}
        {textField('pool')}
        {textField('egress_interface', { span: kind === 'l2tp' })}
        {kind === 'l2tp' && textField('psk', { secret: true, span: true })}
        {arrayField('dns')}
        {arrayField('ike_proposals')}
        {arrayField('esp_proposals')}

        {kind === 'ikev2' && (
          <>
            <SecretTextarea
              id="ipsec-ca-cert"
              label={t('coreEditor.ipsec.fields.ca_cert')}
              value={draft.ca_cert ?? ''}
              placeholder={t('coreEditor.ipsec.placeholders.ca_cert')}
              onChange={value => updateString('ca_cert', value)}
            />
            <SecretTextarea
              id="ipsec-server-cert"
              label={t('coreEditor.ipsec.fields.server_cert')}
              value={draft.server_cert ?? ''}
              placeholder={t('coreEditor.ipsec.placeholders.server_cert')}
              onChange={value => updateString('server_cert', value)}
            />
            <SecretTextarea
              id="ipsec-server-key"
              label={t('coreEditor.ipsec.fields.server_key')}
              value={draft.server_key ?? ''}
              placeholder={t('coreEditor.ipsec.placeholders.server_key')}
              onChange={value => updateString('server_key', value)}
            />
          </>
        )}
      </div>
    </div>
  )
}
