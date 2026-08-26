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
import { getNodes, type NodeResponse } from '@/service/api'
import {
  createHpxTunnel,
  getHpxTunnelPreflight,
  getHpxPanelPublicIp,
  type HpxPreflightResponse,
} from '@/service/api/hpx-tunnels'
import { Check, Server, Shield, Sparkles } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

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
  const [nodes, setNodes] = useState<NodeResponse[]>([])
  const [foreignHost, setForeignHost] = useState<'panel' | 'node'>('node')
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
        label: t('hpxTunnel.wizard.foreignStep', { defaultValue: 'FOREIGN host' }),
        hint: t('hpxTunnel.wizard.foreignHint', { defaultValue: 'Panel or Node VPS' }),
      },
      {
        id: 1,
        label: t('hpxTunnel.wizard.iranStep', { defaultValue: 'IRAN (VPS agent)' }),
        hint: t('hpxTunnel.wizard.iranHint', { defaultValue: 'Join token · Node IP' }),
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
    setForeignHost('node')
    const pwd = generatePassword()
    setSharedPassword(pwd)
    foreignForm.reset({ name: 'hpx_foreign', password: pwd })
    iranForm.reset({ name: 'hpx_iran', remote_ip: '' })
    ;(async () => {
      try {
        const [pf, ipRes, nodesRes] = await Promise.all([
          getHpxTunnelPreflight(),
          getHpxPanelPublicIp(),
          getNodes({ limit: 200 }),
        ])
        setPreflight(pf)
        if (ipRes.ip) setPanelIp(ipRes.ip)
        const list = nodesRes?.nodes ?? []
        setNodes(list)
        const preferred = list.find(n => n.status === 'connected') || list[0]
        if (preferred?.address) iranForm.setValue('remote_ip', preferred.address)
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
                  {t('hpxTunnel.wizard.foreignWhere', {
                    defaultValue: 'Where does FOREIGN run? Usually on a Node VPS — not the panel.',
                  })}
                </p>
              </div>

              <div className="grid gap-2 sm:grid-cols-2">
                <Button
                  type="button"
                  variant={foreignHost === 'node' ? 'default' : 'outline'}
                  className="h-auto flex-col items-start gap-1 py-3"
                  onClick={() => setForeignHost('node')}
                >
                  <span className="font-semibold">{t('hpxTunnel.wizard.onNode', { defaultValue: 'On a Node / external VPS' })}</span>
                  <span className="text-xs font-normal opacity-80">
                    {t('hpxTunnel.wizard.onNodeHint', { defaultValue: 'Recommended — pick Node IP for IRAN remote' })}
                  </span>
                </Button>
                <Button
                  type="button"
                  variant={foreignHost === 'panel' ? 'default' : 'outline'}
                  className="h-auto flex-col items-start gap-1 py-3"
                  onClick={() => setForeignHost('panel')}
                >
                  <span className="font-semibold">{t('hpxTunnel.wizard.onPanel', { defaultValue: 'On this panel server' })}</span>
                  <span className="text-xs font-normal opacity-80">
                    {t('hpxTunnel.wizard.onPanelHint', { defaultValue: 'Starts Docker FOREIGN here' })}
                  </span>
                </Button>
              </div>

              {foreignHost === 'node' ? (
                <div className="space-y-4">
                  <Form {...foreignForm}>
                    <FormField
                      control={foreignForm.control}
                      name="password"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>{t('password', { defaultValue: 'Shared password' })}</FormLabel>
                          <div className="flex gap-2">
                            <FormControl>
                              <PasswordInput {...field} dir="ltr" className="font-mono" />
                            </FormControl>
                            <Button type="button" variant="outline" size="icon" onClick={() => field.onChange(generatePassword())}>
                              <Sparkles className="size-4" />
                            </Button>
                          </div>
                          <p className="text-muted-foreground text-xs">
                            {t('hpxTunnel.wizard.nodeForeignCmd', {
                              defaultValue: 'On the Node VPS run FOREIGN Docker with this password (listen 0.0.0.0, local 10.200.200.1).',
                            })}
                          </p>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </Form>
                  <div className="flex justify-end gap-2">
                    <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                      {t('cancel', { defaultValue: 'Cancel' })}
                    </Button>
                    <Button
                      type="button"
                      onClick={() => {
                        setSharedPassword(foreignForm.getValues('password'))
                        setStep(1)
                      }}
                    >
                      {t('hpxTunnel.wizard.nextIran', { defaultValue: 'Next: IRAN' })}
                    </Button>
                  </div>
                </div>
              ) : (
                <Form {...foreignForm}>
                  <form onSubmit={foreignForm.handleSubmit(createForeign)} className="space-y-4">
                    {preflight && (
                      <p className="text-muted-foreground text-xs">
                        {preflight.ready
                          ? t('hpxTunnel.wizard.preflightOk', { defaultValue: 'Docker + docker.sock + NET_ADMIN ready.' })
                          : preflight.message || t('hpxTunnel.wizard.preflightBad', { defaultValue: 'Host preflight failed.' })}
                      </p>
                    )}
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
                            <Button type="button" variant="outline" size="icon" onClick={() => field.onChange(generatePassword())}>
                              <Sparkles className="size-4" />
                            </Button>
                          </div>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                    <div className="flex justify-end gap-2">
                      <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                        {t('cancel', { defaultValue: 'Cancel' })}
                      </Button>
                      <LoaderButton type="submit" loading={busy}>
                        <Server className="size-4" />
                        {t('hpxTunnel.wizard.startForeign', { defaultValue: 'Start FOREIGN on panel' })}
                      </LoaderButton>
                    </div>
                  </form>
                </Form>
              )}
            </div>
          )}

          {step === 1 && (
            <div className="space-y-4">
              <div className="rounded-lg border border-violet-500/30 bg-violet-500/5 px-4 py-3 text-sm">
                {t('hpxTunnel.wizard.iranBanner', {
                  defaultValue:
                    'IRAN Remote IP = public IP of the host running FOREIGN (usually a Node). Do not use panel IP unless FOREIGN runs on the panel.',
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
                  {nodes.length > 0 && (
                    <div className="space-y-2">
                      <label className="text-sm font-medium">
                        {t('hpxTunnel.wizard.pickNode', { defaultValue: 'Pick Node (FOREIGN host)' })}
                      </label>
                      <Select
                        onValueChange={value => {
                          const node = nodes.find(n => String(n.id) === value)
                          if (node?.address) iranForm.setValue('remote_ip', node.address)
                        }}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder={t('hpxTunnel.wizard.pickNodePlaceholder', { defaultValue: 'Select a node…' })} />
                        </SelectTrigger>
                        <SelectContent>
                          {nodes.map(node => (
                            <SelectItem key={node.id} value={String(node.id)}>
                              {node.name} — {node.address} ({node.status})
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  )}
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
                          {panelIp && (
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              onClick={() => field.onChange(panelIp)}
                              title={t('hpxTunnel.wizard.usePanelIp', { defaultValue: 'Use panel IP' })}
                            >
                              Panel
                            </Button>
                          )}
                        </div>
                        <p className="text-muted-foreground text-xs">
                          {t('hpxTunnel.wizard.remoteIpHint', {
                            defaultValue: 'Must match the VPS where FOREIGN Docker listens (Node IP preferred).',
                          })}
                        </p>
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
                  <li>
                    {foreignHost === 'node'
                      ? t('hpxTunnel.wizard.checklistNodeForeign', {
                          defaultValue: 'FOREIGN Docker must run on the Node VPS (same password, 10.200.200.1).',
                        })
                      : t('hpxTunnel.wizard.checklistForeign', { defaultValue: 'FOREIGN is running on this panel server.' })}
                  </li>
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
