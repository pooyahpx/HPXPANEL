import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { LoaderButton } from '@/components/ui/loader-button'
import { PasswordInput } from '@/components/ui/password-input'
import useDirDetection from '@/hooks/use-dir-detection'
import useDynamicErrorHandler from '@/hooks/use-dynamic-errors'
import HpxJoinTokenDialog, { type JoinTokenPayload } from '@/features/hpx-tunnels/dialogs/hpx-join-token-dialog'
import { cn } from '@/lib/utils'
import {
  createHpxTunnel,
  getHpxTunnelPreflight,
  getHpxPanelPublicIp,
  type HpxPreflightResponse,
} from '@/service/api/hpx-tunnels'
import { Check, RefreshCw, Server, Shield, Sparkles } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'

interface HpxTunnelWizardProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
}

const foreignSchema = z.object({
  name: z.string().min(1).max(128),
  password: z.string().min(4).max(128),
})

const iranSchema = z.object({
  name: z.string().min(1).max(128),
  remote_ip: z.string().min(7).max(45),
})

type ForeignValues = z.infer<typeof foreignSchema>
type IranValues = z.infer<typeof iranSchema>

function generatePassword() {
  const chars = 'abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'
  return Array.from({ length: 16 }, () => chars[Math.floor(Math.random() * chars.length)]).join('')
}

export default function HpxTunnelWizard({ open, onOpenChange, onSuccess }: HpxTunnelWizardProps) {
  const { t } = useTranslation()
  const dir = useDirDetection()
  const handleError = useDynamicErrorHandler()
  const [step, setStep] = useState(0)
  const [busy, setBusy] = useState(false)
  const [preflight, setPreflight] = useState<HpxPreflightResponse | null>(null)
  const [panelIp, setPanelIp] = useState<string | null>(null)
  const [sharedPassword, setSharedPassword] = useState('')
  const [foreignTunnelId, setForeignTunnelId] = useState<number | null>(null)
  const [joinPayload, setJoinPayload] = useState<JoinTokenPayload | null>(null)
  const [joinOpen, setJoinOpen] = useState(false)

  const foreignForm = useForm<ForeignValues>({
    resolver: zodResolver(foreignSchema),
    defaultValues: { name: 'hpx_foreign', password: generatePassword() },
  })

  const iranForm = useForm<IranValues>({
    resolver: zodResolver(iranSchema),
    defaultValues: { name: 'hpx_iran', remote_ip: '' },
  })

  const wizardSteps = useMemo(
    () => [
      {
        id: 0,
        label: t('hpxTunnel.wizard.foreignStep', { defaultValue: 'FOREIGN (this server)' }),
        hint: t('hpxTunnel.wizard.foreignHint', { defaultValue: 'Panel host · ICMP listen' }),
      },
      {
        id: 1,
        label: t('hpxTunnel.wizard.iranStep', { defaultValue: 'IRAN (VPS agent)' }),
        hint: t('hpxTunnel.wizard.iranHint', { defaultValue: 'Join token · remote IP' }),
      },
      {
        id: 2,
        label: t('hpxTunnel.wizard.doneStep', { defaultValue: 'Done' }),
        hint: t('hpxTunnel.wizard.doneHint', { defaultValue: 'Run agent once' }),
      },
    ],
    [t],
  )

  useEffect(() => {
    if (!open) return
    setStep(0)
    setForeignTunnelId(null)
    const pwd = generatePassword()
    setSharedPassword(pwd)
    foreignForm.reset({ name: 'hpx_foreign', password: pwd })
    iranForm.reset({ name: 'hpx_iran', remote_ip: '' })
    ;(async () => {
      try {
        const [pf, ipRes] = await Promise.all([getHpxTunnelPreflight(), getHpxPanelPublicIp()])
        setPreflight(pf)
        if (ipRes.ip) {
          setPanelIp(ipRes.ip)
          iranForm.setValue('remote_ip', ipRes.ip)
        }
      } catch {
        setPreflight(null)
      }
    })()
  }, [open, foreignForm, iranForm])

  const createForeign = async (values: ForeignValues) => {
    setBusy(true)
    try {
      setSharedPassword(values.password)
      const result = await createHpxTunnel({
        name: values.name,
        role: 'foreign',
        password: values.password,
        server_listen: '0.0.0.0',
        interface: 'hpx0',
        local_ip: '10.200.200.1',
        mtu: 1000,
        keepalive: 30,
        start_after_create: true,
      })
      if (result.tunnel.status === 'error') {
        toast.error(t('hpxTunnel.wizard.foreignFailed', { defaultValue: 'FOREIGN start failed' }), {
          description: result.message || undefined,
        })
      } else {
        toast.success(t('hpxTunnel.wizard.foreignReady', { defaultValue: 'FOREIGN tunnel started on panel host' }))
      }
      setForeignTunnelId(result.tunnel.id)
      setStep(1)
      onSuccess?.()
    } catch (error) {
      handleError(error)
    } finally {
      setBusy(false)
    }
  }

  const createIran = async (values: IranValues) => {
    setBusy(true)
    try {
      const result = await createHpxTunnel({
        name: values.name,
        role: 'iran',
        password: sharedPassword || foreignForm.getValues('password'),
        remote_ip: values.remote_ip,
        interface: 'hpx0',
        local_ip: '10.200.200.2',
        mtu: 1000,
        keepalive: 30,
        start_after_create: false,
      })
      if (result.join_token && result.join_command) {
        setJoinPayload({
          join_token: result.join_token,
          join_command: result.join_command,
          join_expires_at: result.join_expires_at,
        })
      }
      setStep(2)
      onSuccess?.()
    } catch (error) {
      handleError(error)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent dir={dir} className={cn('max-h-[90vh] overflow-y-auto sm:max-w-2xl', dir === 'rtl' && 'text-right')}>
          <DialogHeader>
            <DialogTitle>{t('hpxTunnel.wizard.title', { defaultValue: 'New ICMP tunnel wizard' })}</DialogTitle>
            <DialogDescription>
              {t('hpxTunnel.wizard.description', {
                defaultValue: 'FOREIGN runs on this panel server (ICMP, no TCP port). IRAN connects via the lightweight agent on your Iran VPS.',
              })}
            </DialogDescription>
          </DialogHeader>

          <div className="mb-4 flex flex-wrap gap-2" aria-label={t('hpxTunnel.wizard.steps', { defaultValue: 'Steps' })}>
            {wizardSteps.map((s, i) => (
              <button
                key={s.id}
                type="button"
                onClick={() => i < step && setStep(i)}
                className={cn(
                  'flex min-w-[140px] flex-1 items-start gap-2 rounded-lg border px-3 py-2 text-start transition-colors',
                  step === s.id ? 'border-primary bg-primary/5' : step > s.id ? 'border-primary/40' : 'border-border',
                )}
              >
                <span
                  className={cn(
                    'flex size-7 shrink-0 items-center justify-center rounded-full border text-xs font-bold',
                    step === s.id ? 'border-primary bg-primary text-primary-foreground' : step > s.id ? 'border-primary/50 text-primary' : 'border-border',
                  )}
                >
                  {step > s.id ? <Check className="size-3.5" /> : `0${i + 1}`}
                </span>
                <span className="min-w-0">
                  <span className="block truncate text-xs font-bold">{s.label}</span>
                  <span className="text-muted-foreground block truncate text-[10px]">{s.hint}</span>
                </span>
              </button>
            ))}
          </div>

          {step === 0 && (
            <div className="space-y-4">
              <div className="rounded-lg border border-blue-500/30 bg-blue-500/5 px-4 py-3 text-sm">
                <p className="font-medium text-blue-700 dark:text-blue-300">
                  {t('hpxTunnel.wizard.foreignBanner', {
                    defaultValue: 'FOREIGN runs on this panel server — ICMP only, no open port required.',
                  })}
                </p>
                {preflight && (
                  <p className="text-muted-foreground mt-1 text-xs">
                    {preflight.ready
                      ? t('hpxTunnel.wizard.preflightOk', { defaultValue: 'Docker + docker.sock + NET_ADMIN ready.' })
                      : preflight.message || t('hpxTunnel.wizard.preflightBad', { defaultValue: 'Host preflight failed — check compose mounts.' })}
                  </p>
                )}
              </div>

              <Form {...foreignForm}>
                <form onSubmit={foreignForm.handleSubmit(createForeign)} className="space-y-4">
                  <FormField
                    control={foreignForm.control}
                    name="name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('name', { defaultValue: 'Name' })}</FormLabel>
                        <FormControl>
                          <Input {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={foreignForm.control}
                    name="password"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('password', { defaultValue: 'Password' })}</FormLabel>
                        <div className="flex gap-2">
                          <FormControl>
                            <PasswordInput {...field} dir="ltr" className="font-mono" />
                          </FormControl>
                          <Button
                            type="button"
                            variant="outline"
                            size="icon"
                            onClick={() => field.onChange(generatePassword())}
                            title={t('hpxTunnel.wizard.generatePassword', { defaultValue: 'Generate' })}
                          >
                            <Sparkles className="size-4" />
                          </Button>
                        </div>
                        <p className="text-muted-foreground text-xs">
                          {t('hpxTunnel.wizard.sharedPassword', { defaultValue: 'Same password will be used for IRAN in step 2.' })}
                        </p>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <div className="text-muted-foreground grid gap-1 rounded-md border bg-muted/30 p-3 text-xs font-mono">
                    <div>Listen: 0.0.0.0 · MTU: 1000 · Keepalive: 30s</div>
                    <div>Local IP: 10.200.200.1 · Interface: hpx0</div>
                  </div>
                  <div className="flex justify-end gap-2">
                    <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                      {t('cancel', { defaultValue: 'Cancel' })}
                    </Button>
                    <LoaderButton type="submit" loading={busy}>
                      <Server className="size-4" />
                      {t('hpxTunnel.wizard.startForeign', { defaultValue: 'Start FOREIGN' })}
                    </LoaderButton>
                  </div>
                </form>
              </Form>
            </div>
          )}

          {step === 1 && (
            <div className="space-y-4">
              <div className="rounded-lg border border-violet-500/30 bg-violet-500/5 px-4 py-3 text-sm">
                {t('hpxTunnel.wizard.iranBanner', {
                  defaultValue: 'IRAN uses the agent on your VPS. Remote IP = public IP of this panel server (FOREIGN). No port — only ICMP between the two IPs.',
                })}
              </div>

              <Form {...iranForm}>
                <form onSubmit={iranForm.handleSubmit(createIran)} className="space-y-4">
                  <FormField
                    control={iranForm.control}
                    name="name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('name', { defaultValue: 'Name' })}</FormLabel>
                        <FormControl>
                          <Input {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={iranForm.control}
                    name="remote_ip"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('hpxTunnel.remoteIp', { defaultValue: 'Remote IP (FOREIGN server)' })}</FormLabel>
                        <div className="flex gap-2">
                          <FormControl>
                            <Input {...field} dir="ltr" className="font-mono" />
                          </FormControl>
                          <Button
                            type="button"
                            variant="outline"
                            size="icon"
                            onClick={async () => {
                              try {
                                const res = await getHpxPanelPublicIp()
                                if (res.ip) {
                                  field.onChange(res.ip)
                                  setPanelIp(res.ip)
                                }
                              } catch {
                                /* ignore */
                              }
                            }}
                          >
                            <RefreshCw className="size-4" />
                          </Button>
                        </div>
                        {panelIp && (
                          <p className="text-muted-foreground text-xs">
                            {t('hpxTunnel.wizard.panelIpHint', { defaultValue: 'Suggested panel public IP: {{ip}}', ip: panelIp })}
                          </p>
                        )}
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <div className="text-muted-foreground grid gap-1 rounded-md border bg-muted/30 p-3 text-xs font-mono">
                    <div>MTU: 1000 · Keepalive: 30s · Local IP: 10.200.200.2</div>
                  </div>
                  <div className="flex justify-between gap-2">
                    <Button type="button" variant="ghost" onClick={() => setStep(0)}>
                      {t('back', { defaultValue: 'Back' })}
                    </Button>
                    <LoaderButton type="submit" loading={busy}>
                      <Shield className="size-4" />
                      {t('hpxTunnel.wizard.createIran', { defaultValue: 'Create IRAN + join token' })}
                    </LoaderButton>
                  </div>
                </form>
              </Form>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-4">
              <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 px-4 py-3 text-sm">
                <p className="font-medium text-emerald-700 dark:text-emerald-300">
                  {t('hpxTunnel.wizard.doneTitle', { defaultValue: 'Tunnels configured' })}
                </p>
                <ul className="text-muted-foreground mt-2 list-inside list-disc space-y-1 text-xs">
                  <li>{t('hpxTunnel.wizard.checklistForeign', { defaultValue: 'FOREIGN is running on this panel server.' })}</li>
                  <li>{t('hpxTunnel.wizard.checklistAgent', { defaultValue: 'Run the Iran agent installer once — paste the join token when asked.' })}</li>
                  <li>{t('hpxTunnel.wizard.checklistPing', { defaultValue: 'Ping 10.200.200.x between ends after agent connects.' })}</li>
                </ul>
              </div>
              {joinPayload && (
                <Button type="button" variant="secondary" onClick={() => setJoinOpen(true)}>
                  {t('hpxTunnel.agent.joinTitle', { defaultValue: 'Show join token' })}
                </Button>
              )}
              {foreignTunnelId && (
                <p className="text-muted-foreground text-xs">
                  {t('hpxTunnel.wizard.foreignId', { defaultValue: 'FOREIGN tunnel ID: {{id}}', id: foreignTunnelId })}
                </p>
              )}
              <div className="flex justify-end">
                <Button onClick={() => onOpenChange(false)}>{t('close', { defaultValue: 'Close' })}</Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
      <HpxJoinTokenDialog open={joinOpen} onOpenChange={setJoinOpen} payload={joinPayload} />
    </>
  )
}
