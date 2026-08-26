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
import { toBackpackPortString } from '@/features/hpx-pulse/utils/port-forwards'
import {
  useAdvisePulse,
  useCreateHpxPulse,
  type HpxPulseActionResponse,
  type PulseAdviseResponse,
} from '@/service/api/hpx-pulse'
import { zodResolver } from '@hookform/resolvers/zod'
import { Sparkles, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { z } from 'zod'

const portForwardSchema = z.object({
  external_port: z.coerce.number().int().min(1).max(65535),
  internal_ip: z.string().max(45).optional().default(''),
  internal_port: z.coerce.number().int().min(1).max(65535),
})

const schema = z.object({
  name: z.string().min(1).max(40),
  iran_public_ip: z.string().min(7),
  abroad_public_ip: z.string().min(7),
  goal: z.enum(['stealth', 'balanced', 'speed']),
  cpu_cores: z.coerce.number().int().min(1).max(128),
  ram_mb: z.coerce.number().int().min(256),
  udp_reachable: z.enum(['unknown', 'yes', 'no']),
  packet_loss_pct: z.coerce.number().min(0).max(100).optional(),
  control_port: z.coerce.number().int().min(1024).max(65535),
  port_forwards: z.array(portForwardSchema).default([]),
  domain: z.string().optional(),
  sni_hint: z.string().optional(),
})

type FormValues = z.infer<typeof schema>

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
      name: 'pulse_main',
      iran_public_ip: '',
      abroad_public_ip: '',
      goal: 'balanced',
      cpu_cores: 1,
      ram_mb: 1024,
      udp_reachable: 'unknown',
      packet_loss_pct: 0,
      control_port: 9067,
      port_forwards: [],
      domain: '',
      sni_hint: 'play.google.com',
    },
  })

  useEffect(() => {
    if (!open) {
      setAdvice(null)
      setSelectedProfile(null)
    }
  }, [open])

  const runAdvise = async () => {
    const v = form.getValues()
    try {
      const res = await adviseMutation.mutateAsync({
        cpu_cores: v.cpu_cores,
        ram_mb: v.ram_mb,
        goal: v.goal,
        packet_loss_pct: v.packet_loss_pct,
        udp_reachable: v.udp_reachable === 'unknown' ? null : v.udp_reachable === 'yes',
      })
      setAdvice(res)
      setSelectedProfile(res.recommended_profile_id)
    } catch (e) {
      handleError(e)
    }
  }

  const create = async (values: FormValues) => {
    try {
      const res = await createMutation.mutateAsync({
        name: values.name,
        iran_public_ip: values.iran_public_ip,
        abroad_public_ip: values.abroad_public_ip,
        goal: values.goal,
        cpu_cores: values.cpu_cores,
        ram_mb: values.ram_mb,
        udp_reachable: values.udp_reachable === 'unknown' ? null : values.udp_reachable === 'yes',
        packet_loss_pct: values.packet_loss_pct,
        profile_id: selectedProfile ?? advice?.recommended_profile_id,
        control_port: values.control_port,
        port_forwards: values.port_forwards.map(toBackpackPortString),
        domain: values.domain || null,
        sni_hint: values.sni_hint || null,
      })
      onCreated?.(res)
      onOpenChange(false)
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
              defaultValue: 'Smart profile picker for BackPack Direct + Reality front on Iran.',
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
                  <FormControl><Input {...field} dir="ltr" /></FormControl>
                </FormItem>
              )} />
              <FormField control={form.control} name="abroad_public_ip" render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('hpxPulse.abroadIp', { defaultValue: 'Abroad public IP' })}</FormLabel>
                  <FormControl><Input {...field} dir="ltr" /></FormControl>
                </FormItem>
              )} />
              <FormField control={form.control} name="cpu_cores" render={({ field }) => (
                <FormItem>
                  <FormLabel>CPU cores</FormLabel>
                  <FormControl><Input type="number" {...field} /></FormControl>
                </FormItem>
              )} />
              <FormField control={form.control} name="ram_mb" render={({ field }) => (
                <FormItem>
                  <FormLabel>RAM (MB)</FormLabel>
                  <FormControl><Input type="number" {...field} /></FormControl>
                </FormItem>
              )} />
              <FormField control={form.control} name="domain" render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('hpxPulse.domain', { defaultValue: 'Domain on Iran' })}</FormLabel>
                  <FormControl><Input {...field} dir="ltr" placeholder="vpn.example.com" /></FormControl>
                </FormItem>
              )} />
              <FormField control={form.control} name="sni_hint" render={({ field }) => (
                <FormItem>
                  <FormLabel>Reality SNI</FormLabel>
                  <FormControl><Input {...field} dir="ltr" /></FormControl>
                </FormItem>
              )} />
              <FormField control={form.control} name="control_port" render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('hpxPulse.tunnelPort', { defaultValue: 'Tunnel port' })}</FormLabel>
                  <FormControl><Input type="number" {...field} dir="ltr" /></FormControl>
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
                  {t('hpxPulse.addPortForward', { defaultValue: 'Add rule' })}
                </Button>
              </div>
              <p className="text-muted-foreground text-xs">
                {t('hpxPulse.portForwardsHint', {
                  defaultValue: 'BackPack syntax on Iran: 443, 443=8443, or 443=10.0.0.5:8443. Empty internal IP uses tunnel peer.',
                })}
              </p>
              {form.watch('port_forwards').map((_, index) => (
                <div key={index} className="grid gap-2 sm:grid-cols-[1fr_1.2fr_1fr_auto]">
                  <FormField control={form.control} name={`port_forwards.${index}.external_port`} render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-xs">{t('hpxPulse.externalPort', { defaultValue: 'External' })}</FormLabel>
                      <FormControl><Input type="number" {...field} dir="ltr" /></FormControl>
                    </FormItem>
                  )} />
                  <FormField control={form.control} name={`port_forwards.${index}.internal_ip`} render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-xs">{t('hpxPulse.internalIp', { defaultValue: 'Internal IP (optional)' })}</FormLabel>
                      <FormControl><Input {...field} dir="ltr" placeholder="10.10.0.2" /></FormControl>
                    </FormItem>
                  )} />
                  <FormField control={form.control} name={`port_forwards.${index}.internal_port`} render={({ field }) => (
                    <FormItem>
                      <FormLabel className="text-xs">{t('hpxPulse.internalPort', { defaultValue: 'Internal port' })}</FormLabel>
                      <FormControl><Input type="number" {...field} dir="ltr" /></FormControl>
                    </FormItem>
                  )} />
                  <Button
                    type="button"
                    size="icon"
                    variant="ghost"
                    className="mt-6"
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

            <Button type="button" variant="secondary" onClick={runAdvise} disabled={adviseMutation.isPending}>
              <Sparkles className="size-4" />
              {t('hpxPulse.advise', { defaultValue: 'Get AI recommendation' })}
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
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium">{fa ? p.title_fa : p.title}</span>
                      <Badge variant="secondary">{p.score}</Badge>
                    </div>
                    <p className="text-muted-foreground mt-1">{fa ? p.reasons_fa[0] : p.reasons[0]}</p>
                  </button>
                ))}
                <ul className="text-muted-foreground list-inside list-disc text-xs">
                  {(fa ? advice.reality_front.checklist_fa : advice.reality_front.checklist).map(line => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                {t('cancel', { defaultValue: 'Cancel' })}
              </Button>
              <LoaderButton type="submit" loading={createMutation.isPending} disabled={!advice}>
                {t('hpxPulse.create', { defaultValue: 'Create Pulse' })}
              </LoaderButton>
            </div>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
