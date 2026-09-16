import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import { XrayAdvancedSection } from '@/features/core-editor/components/xray/xray-advanced-section'
import { isCredentialVpnKind } from '@/features/core-editor/kit/credential-vpn-config'
import { useCoreEditorStore, type IpsecCoreSection } from '@/features/core-editor/state/core-editor-store'
import { cn } from '@/lib/utils'
import { useTranslation } from 'react-i18next'

export function CredentialVpnCoreEditor() {
  const { t } = useTranslation()
  const kind = useCoreEditorStore(s => s.kind)
  const section = useCoreEditorStore(s => s.activeSection) as IpsecCoreSection
  const draft = useCoreEditorStore(s => s.credentialVpnDraft)
  const updateDraft = useCoreEditorStore(s => s.updateCredentialVpnDraft)

  if (!isCredentialVpnKind(kind) || !draft) return null
  if (section === 'advanced') return <XrayAdvancedSection />

  const field = (key: keyof typeof draft, options?: { span?: boolean; type?: string }) => (
    <div className={cn('space-y-2', options?.span && 'sm:col-span-2')}>
      <Label htmlFor={`cvpn-${String(key)}`}>{t(`coreEditor.credentialVpn.fields.${String(key)}`, { defaultValue: String(key) })}</Label>
      <Input
        id={`cvpn-${String(key)}`}
        type={options?.type ?? 'text'}
        value={String(draft[key] ?? '')}
        onChange={event => {
          const raw = event.target.value
          updateDraft(current => ({
            ...current,
            [key]: key === 'port' || key === 'fou_port' ? Number(raw) || 0 : raw,
          }))
        }}
        dir="ltr"
      />
    </div>
  )

  return (
    <div className="space-y-4 px-4 py-4 md:px-6">
      <p className="text-muted-foreground max-w-3xl text-sm">
        {t(`coreEditor.credentialVpn.description.${kind}`, { defaultValue: t('coreEditor.credentialVpn.description.generic') })}
      </p>
      <div className="grid gap-4 sm:grid-cols-2">
        {field('inbound_tag')}
        {field('server_addr')}
        {field('port', { type: 'number' })}
        {kind !== 'ssh' && kind !== 'mtproto' ? field('pool') : null}
        {kind === 'openconnect' ? field('protocol') : null}
        {kind === 'ssh' ? field('banner', { span: true }) : null}
        {kind === 'gre' ? (
          <>
            {field('peer_addr')}
            {field('local_addr')}
            {field('fou_port', { type: 'number' })}
            <div className="flex items-center justify-between gap-3 rounded-md border p-3 sm:col-span-2">
              <div className="space-y-1">
                <Label htmlFor="cvpn-ipsec">{t('coreEditor.credentialVpn.fields.ipsec')}</Label>
                <p className="text-muted-foreground text-xs">{t('coreEditor.credentialVpn.ipsecHint')}</p>
              </div>
              <Switch id="cvpn-ipsec" checked={Boolean(draft.ipsec)} onCheckedChange={checked => updateDraft(current => ({ ...current, ipsec: checked }))} />
            </div>
          </>
        ) : null}
        {kind === 'mtproto' ? (
          <>
            {field('mode')}
            <div className="space-y-2 sm:col-span-2">
              <Label htmlFor="cvpn-secret">{t('coreEditor.credentialVpn.fields.secret')}</Label>
              <Textarea
                id="cvpn-secret"
                rows={3}
                value={draft.secret || ''}
                onChange={event => updateDraft(current => ({ ...current, secret: event.target.value }))}
                dir="ltr"
                className="font-mono text-xs"
              />
            </div>
          </>
        ) : null}
        {kind !== 'ssh' && kind !== 'mtproto' ? (
          <div className="space-y-2 sm:col-span-2">
            <Label htmlFor="cvpn-dns">{t('coreEditor.credentialVpn.fields.dns')}</Label>
            <Textarea
              id="cvpn-dns"
              rows={3}
              value={(draft.dns || []).join('\n')}
              onChange={event =>
                updateDraft(current => ({
                  ...current,
                  dns: event.target.value
                    .split('\n')
                    .map(item => item.trim())
                    .filter(Boolean),
                }))
              }
              dir="ltr"
              className="font-mono text-xs"
            />
          </div>
        ) : null}
      </div>
      <p className="text-muted-foreground text-xs">{t('coreEditor.credentialVpn.nodePending')}</p>
    </div>
  )
}
