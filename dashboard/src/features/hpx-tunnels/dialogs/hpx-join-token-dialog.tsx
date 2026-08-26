import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import useDirDetection from '@/hooks/use-dir-detection'
import { cn } from '@/lib/utils'
import { Check, Copy, Terminal } from 'lucide-react'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

export interface JoinTokenPayload {
  join_token: string
  join_command: string
  join_expires_at?: string | null
}

interface HpxJoinTokenDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  payload: JoinTokenPayload | null
}

export default function HpxJoinTokenDialog({ open, onOpenChange, payload }: HpxJoinTokenDialogProps) {
  const { t } = useTranslation()
  const dir = useDirDetection()
  const [copied, setCopied] = useState<'token' | 'command' | null>(null)

  const copy = async (value: string, kind: 'token' | 'command') => {
    try {
      await navigator.clipboard.writeText(value)
      setCopied(kind)
      toast.success(t('copied', { defaultValue: 'Copied' }))
      setTimeout(() => setCopied(null), 1500)
    } catch {
      toast.error(t('copyFailed', { defaultValue: 'Copy failed' }))
    }
  }

  if (!payload) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent dir={dir} className={cn('sm:max-w-xl', dir === 'rtl' && 'text-right')}>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Terminal className="size-5" />
            {t('hpxTunnel.agent.joinTitle', { defaultValue: 'Iran agent join token' })}
          </DialogTitle>
          <DialogDescription>
            {t('hpxTunnel.agent.joinDescription', {
              defaultValue: 'On the Iran server run the installer (it asks questions). Paste the secret token when prompted — or use Manual setup and enter the FOREIGN IP yourself.',
            })}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-muted-foreground text-xs font-medium uppercase tracking-wide">
              {t('hpxTunnel.agent.secretToken', { defaultValue: 'Secret token' })}
            </label>
            <div className="flex gap-2">
              <Input value={payload.join_token} readOnly dir="ltr" className="font-mono text-xs" />
              <Button type="button" variant="outline" size="icon" onClick={() => copy(payload.join_token, 'token')}>
                {copied === 'token' ? <Check className="size-4" /> : <Copy className="size-4" />}
              </Button>
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-muted-foreground text-xs font-medium uppercase tracking-wide">
              {t('hpxTunnel.agent.oneLiner', { defaultValue: 'Iran server command' })}
            </label>
            <div className="bg-muted/40 relative rounded-md border p-3">
              <pre className="overflow-x-auto whitespace-pre-wrap break-all font-mono text-[11px] leading-relaxed" dir="ltr">
                {payload.join_command}
              </pre>
              <Button type="button" variant="secondary" size="sm" className="mt-2" onClick={() => copy(payload.join_command, 'command')}>
                {copied === 'command' ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
                {t('hpxTunnel.agent.copyCommand', { defaultValue: 'Copy command' })}
              </Button>
            </div>
          </div>

          {payload.join_expires_at && (
            <p className="text-muted-foreground text-xs">
              {t('hpxTunnel.agent.expiresAt', {
                defaultValue: 'Expires: {{when}}',
                when: new Date(payload.join_expires_at).toLocaleString(),
              })}
            </p>
          )}

          <p className="text-muted-foreground text-xs">
            {t('hpxTunnel.agent.icmpNoPort', {
              defaultValue: 'No port is required — only ICMP between the two public IPs.',
            })}
          </p>
          <p className="text-muted-foreground text-xs">
            {t('hpxTunnel.agent.shownOnce', {
              defaultValue: 'Token is shown once. If lost, regenerate it from the tunnel card.',
            })}
          </p>
        </div>
      </DialogContent>
    </Dialog>
  )
}
