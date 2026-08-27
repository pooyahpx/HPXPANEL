import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { LoaderButton } from '@/components/ui/loader-button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import useDirDetection from '@/hooks/use-dir-detection'
import useDynamicErrorHandler from '@/hooks/use-dynamic-errors'
import { cn } from '@/lib/utils'
import { toTunnelPortString } from '@/features/hpx-pulse/utils/port-forwards'
import {
  useAdvisePulse,
  useCreateHpxPulse,
  type HpxPulseActionResponse,
  type PulseAdviseResponse,
} from '@/service/api/hpx-pulse'
import { zodResolver } from '@hookform/resolvers/zod'
import { Dices, Sparkles, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { z } from 'zod'

const portForwardSchema = z.object({
  external_port: z.coerce.number().int().min(1).max(65535),
  internal_ip: z.string().max(45).optional().default(''),
  internal_port: z.coerce.number().int().min(1).max(65535),
})

const schema = z.object({
  name: z.string().min(1, 'Name required').max(40),
  iran_public_ip: z.string().min(7, 'Iran IP required'),
  abroad_public_ip: z.string().min(7, 'Abroad IP required'),
  goal: z.enum(['stealth', 'balanced', 'speed']),
  control_port: z.coerce.number().int().min(1024).max(65535),
  port_forwards: z.array(portForwardSchema).default([]),
})

type FormValues = z.infer<typeof schema>

function defaultPulseName() {
  const n = new Date()
  return `pulse_${n.getFullYear()}${String(n.getMonth() + 1).padStart(2, '0')}${String(n.getDate()).padStart(2, '0')}_${String(n.getHours()).padStart(2, '0')}${String(n.getMinutes()).padStart(2, '0')}`
}

function randomTunnelPort() {
  return Math.floor(Math.random() * (65500 - 10000 + 1)) + 10000
}

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess?: () => void
  onCreated?: (res: HpxPulseActionResponse) => void
}

export default function HpxPulseWizard({ open, onOpenChange, onCreated }: Props) {
  const { t, i18n } = useTranslation()
  const dir = useDirDetection()
  const fa = i18n.language?.startsWith('fa')
  const handleError = useDynamicErrorHandler()
  const adviseMutation = useAdvisePulse()
  const createMutation = useCreateHpxPulse()
  const [advice, setAdvice] = useState<PulseAdviseResponse | null>(null)
  const [selectedProfile, setSelectedProfile] = useState<string | null>(null)

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: defaultPulseName(),
      iran_public_ip: '',
      abroad_public_ip: '',
      goal: 'balanced',
      control_port: randomTunnelPort(),
      port_forwards: [{ external_port: 443, internal_ip: '', internal_port: 443 }],
    },
  })

  useEffect(() => {
    if (open) {
      form.reset({
        name: defaultPulseName(),
        iran_public_ip: '',
        abroad_public_ip: '',
        goal: 'balanced',
        control_port: randomTunnelPort(),
        port_forwards: [{ external_port: 443, internal_ip: '', internal_port: 443 }],
      })
      setAdvice(null)
      setSelectedProfile(null)
    }
  }, [open, form])

  const runAdvise = async (values?: FormValues) => {
    const v = values ?? form.getValues()
    const res = await adviseMutation.mutateAsync({
      cpu_cores: 1,
      ram_mb: 1024,
      goal: v.goal,
      packet_loss_pct: 0,
      udp_reachable: null,
    })
    setAdvice(res)
    setSelectedProfile(res.recommended_profile_id)
    return res
  }

  const create = async (values: FormValues) => {
    try {
      let profileId = selectedProfile ?? advice?.recommended_profile_id
      if (!profileId) {
        const res = await runAdvise(values)
        profileId = res.recommended_profile_id
      }

      const res = await createMutation.mutateAsync({
        name: values.name.trim(),
        iran_public_ip: values.iran_public_ip.trim(),
        abroad_public_ip: values.abroad_public_ip.trim(),
        goal: values.goal,
        cpu_cores: 1,
        ram_mb: 1024,
        udp_reachable: null,
        packet_loss_pct: 0,
        profile_id: profileId,
        control_port: values.control_port,
        port_forwards: (values.port_forwards ?? []).map(toTunnelPortString),
      })
      toast.success(t('hpxPulse.createSuccess', { defaultValue: 'Pulse created — copy install commands below' }))
      onCreated?.(res)
      onOpenChange(false)
    } catch (e) {
      handleError(e)
    }
  }

  const previewAdvise = async () => {
    const valid = await form.trigger(['goal'])
    if (!valid) return
    try {
      await runAdvise()
    } catch (e) {
      handleError(e)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent dir={dir} className={cn('max-h-[90vh] overflow-y-auto sm:max-w-2xl', dir === 'rtl' && 'text-right')}>
        <DialogHeader>
          <DialogTitle>{t('hpxPulse.wizard.title', { defaultValue: 'HPX Pulse Advisor' })}</DialogTitle>
          <DialogDescription>
            {t('hpxPulse.wizard.description', {
              defaultValue: 'Enter host facts, get ranked HPX Reverse/Direct profiles, then deploy Iran and abroad agents.',
            })}
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(create)} className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-2">
              <FormField control={form.control} name="name" render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('name', { defaultValue: 'Name' })}</FormLabel>
                  <FormControl><Input {...field} /></FormControl>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={form.control} name="goal" render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('hpxPulse.goal', { defaultValue: 'Goal' })}</FormLabel>
                  <Select onValueChange={field.onChange} value={field.value}>
                    <FormControl><SelectTrigger><SelectValue /></SelectTrigger></FormControl>
                    <SelectContent>
                      <SelectItem value="stealth">stealth</SelectItem>
                      <SelectItem value="balanced">balanced</SelectItem>
                      <SelectItem value="speed">speed</SelectItem>
                    </SelectContent>
                  </Select>
                </FormItem>
              )} />
              <FormField control={form.control} name="iran_public_ip" render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('hpxPulse.iranIp', { defaultValue: 'Iran public IP' })}</FormLabel>
                  <FormControl><Input {...field} dir="ltr" placeholder="1.2.3.4" /></FormControl>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={form.control} name="abroad_public_ip" render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('hpxPulse.abroadIp', { defaultValue: 'Abroad public IP' })}</FormLabel>
                  <FormControl><Input {...field} dir="ltr" placeholder="5.6.7.8" /></FormControl>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={form.control} name="control_port" render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('hpxPulse.tunnelPort', { defaultValue: 'Tunnel port' })}</FormLabel>
                  <div className="flex gap-2">
                    <FormControl>
                      <Input type="number" {...field} dir="ltr" />
                    </FormControl>
                    <Button
                      type="button"
                      variant="outline"
                      size="icon"
                      title={t('hpxPulse.randomPort', { defaultValue: 'Random port' })}
                      onClick={() => form.setValue('control_port', randomTunnelPort())}
                    >
                      <Dices className="size-4" />
                    </Button>
                  </div>
                  <FormMessage />
                </FormItem>
              )} />
            </div>

            <div className="space-y-2 rounded-lg border p-3">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-medium">{t('hpxPulse.portForwards', { defaultValue: 'Port forwards' })}</p>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() =>
                    form.setValue('port_forwards', [
                      ...form.getValues('port_forwards'),
                      { external_port: 443, internal_ip: '', internal_port: 443 },
                    ])
                  }
                >
                  {t('hpxPulse.addPortForward', { defaultValue: 'Add' })}
                </Button>
              </div>
              <p className="text-muted-foreground text-xs">
                {t('hpxPulse.portForwardsHint', { defaultValue: 'Iran port → abroad port  (example: 443 → 443)' })}
              </p>
              {form.watch('port_forwards').map((_, index) => (
                <div key={index} className="flex items-end gap-2">
                  <FormField control={form.control} name={`port_forwards.${index}.external_port`} render={({ field }) => (
                    <FormItem className="flex-1">
                      <FormLabel className="text-xs">{t('hpxPulse.iranPort', { defaultValue: 'Iran' })}</FormLabel>
                      <FormControl><Input type="number" {...field} dir="ltr" placeholder="443" /></FormControl>
                    </FormItem>
                  )} />
                  <span className="text-muted-foreground mb-2 text-sm">→</span>
                  <FormField control={form.control} name={`port_forwards.${index}.internal_port`} render={({ field }) => (
                    <FormItem className="flex-1">
                      <FormLabel className="text-xs">{t('hpxPulse.abroadPort', { defaultValue: 'Abroad' })}</FormLabel>
                      <FormControl><Input type="number" {...field} dir="ltr" placeholder="443" /></FormControl>
                    </FormItem>
                  )} />
                  <Button
                    type="button"
                    size="icon"
                    variant="ghost"
                    className="mb-0.5"
                    onClick={() => {
                      const current = form.getValues('port_forwards')
                      form.setValue('port_forwards', current.filter((_, i) => i !== index))
                    }}
                  >
                    <Trash2 className="size-4" />
                  </Button>
                </div>
              ))}
            </div>

            <Button type="button" variant="secondary" onClick={previewAdvise} disabled={adviseMutation.isPending}>
              <Sparkles className="size-4" />
              {t('hpxPulse.advise', { defaultValue: 'Preview recommendation (optional)' })}
            </Button>

            {advice && (
              <div className="space-y-2 rounded-lg border p-3">
                <p className="text-sm font-medium">{t('hpxPulse.profiles', { defaultValue: 'Profiles' })}</p>
                {advice.profiles.map(p => (
                  <button
                    key={p.profile_id}
                    type="button"
                    onClick={() => setSelectedProfile(p.profile_id)}
                    className={cn(
                      'w-full rounded-md border p-2 text-start text-xs transition-colors',
                      (selectedProfile ?? advice.recommended_profile_id) === p.profile_id && 'border-primary bg-primary/5',
                    )}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-medium">{fa ? p.title_fa : p.title}</span>
                      <div className="flex items-center gap-1">
                        {p.tunnel_mode.startsWith('reverse_') && (
                          <Badge variant="outline" className="text-[10px] uppercase">Reverse</Badge>
                        )}
                        {p.carrier && (
                          <Badge variant="secondary" className="text-[10px] uppercase">{p.carrier}</Badge>
                        )}
                        <Badge variant="secondary">{p.score}</Badge>
                      </div>
                    </div>
                    <p className="text-muted-foreground mt-1">{fa ? p.reasons_fa[0] : p.reasons[0]}</p>
                  </button>
                ))}
              </div>
            )}

            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                {t('cancel', { defaultValue: 'Cancel' })}
              </Button>
              <LoaderButton type="submit" loading={createMutation.isPending || adviseMutation.isPending}>
                {t('hpxPulse.create', { defaultValue: 'Create Pulse' })}
              </LoaderButton>
            </div>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
