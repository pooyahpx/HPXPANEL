import { CopyButton } from '@/components/common/copy-button'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { useTranslation } from 'react-i18next'

const CERT_DIR = '/etc/openvpn/easy-rsa'

export const OPENVPN_CERT_SCRIPTS = {
  install: 'apt update && apt install -y easy-rsa openvpn',
  build: [
    `mkdir -p ${CERT_DIR} && cd ${CERT_DIR}`,
    'cp -r /usr/share/easy-rsa/* .',
    './easyrsa init-pki',
    './easyrsa build-ca nopass',
    './easyrsa build-server-full server nopass',
    `openvpn --genkey secret /etc/openvpn/ta.key`,
  ].join('\n'),
  showCa: `cat ${CERT_DIR}/pki/ca.crt`,
  showServerCert: `cat ${CERT_DIR}/pki/issued/server.crt`,
  showServerKey: `cat ${CERT_DIR}/pki/private/server.key`,
  showTlsCrypt: 'cat /etc/openvpn/ta.key',
} as const

function CommandBlock({ label, command, hint }: { label: string; command: string; hint?: string }) {
  return (
    <div className="space-y-1.5 rounded-md border p-3">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium">{label}</p>
        <CopyButton
          value={command}
          className="h-8 w-8 shrink-0"
          copiedMessage="copied"
          defaultMessage="clickToCopy"
          showToast
          toastSuccessMessage="copied"
        />
      </div>
      <pre className="bg-muted overflow-x-auto rounded-md p-2 font-mono text-xs" dir="ltr">
        {command}
      </pre>
      {hint ? <p className="text-muted-foreground text-xs">{hint}</p> : null}
    </div>
  )
}

export function OpenVPNCertHelp() {
  const { t } = useTranslation()

  return (
    <Alert>
      <AlertTitle>{t('coreEditor.openvpn.certHelp.title')}</AlertTitle>
      <AlertDescription className="space-y-4 text-sm">
        <p>{t('coreEditor.openvpn.certHelp.intro')}</p>

        <div className="space-y-2">
          <p className="font-medium">{t('coreEditor.openvpn.certHelp.step1Title')}</p>
          <CommandBlock label={t('coreEditor.openvpn.certHelp.step1Label')} command={OPENVPN_CERT_SCRIPTS.install} />
        </div>

        <div className="space-y-2">
          <p className="font-medium">{t('coreEditor.openvpn.certHelp.step2Title')}</p>
          <CommandBlock
            label={t('coreEditor.openvpn.certHelp.step2Label')}
            command={OPENVPN_CERT_SCRIPTS.build}
            hint={t('coreEditor.openvpn.certHelp.step2Hint')}
          />
        </div>

        <div className="space-y-2">
          <p className="font-medium">{t('coreEditor.openvpn.certHelp.step3Title')}</p>
          <p className="text-muted-foreground text-xs">{t('coreEditor.openvpn.certHelp.step3Hint')}</p>
          <CommandBlock
            label={t('coreEditor.openvpn.fields.ca_cert')}
            command={OPENVPN_CERT_SCRIPTS.showCa}
            hint={t('coreEditor.openvpn.certHelp.pasteInto', { field: t('coreEditor.openvpn.fields.ca_cert') })}
          />
          <CommandBlock
            label={t('coreEditor.openvpn.fields.server_cert')}
            command={OPENVPN_CERT_SCRIPTS.showServerCert}
            hint={t('coreEditor.openvpn.certHelp.pasteInto', { field: t('coreEditor.openvpn.fields.server_cert') })}
          />
          <CommandBlock
            label={t('coreEditor.openvpn.fields.server_key')}
            command={OPENVPN_CERT_SCRIPTS.showServerKey}
            hint={t('coreEditor.openvpn.certHelp.pasteInto', { field: t('coreEditor.openvpn.fields.server_key') })}
          />
          <CommandBlock
            label={t('coreEditor.openvpn.fields.tls_crypt_key')}
            command={OPENVPN_CERT_SCRIPTS.showTlsCrypt}
            hint={t('coreEditor.openvpn.certHelp.pasteIntoOptional', { field: t('coreEditor.openvpn.fields.tls_crypt_key') })}
          />
        </div>

        <p className="text-muted-foreground text-xs">{t('coreEditor.openvpn.certHelp.note')}</p>
      </AlertDescription>
    </Alert>
  )
}
