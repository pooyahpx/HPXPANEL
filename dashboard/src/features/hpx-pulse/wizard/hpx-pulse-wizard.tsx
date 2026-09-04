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
import { toTunnelPortString, fromTunnelPortString } from '@/features/hpx-pulse/utils/port-forwards'
import {
  useAdvisePulse,
  useCreateHpxPulse,
  useUpdateHpxPulse,
  type HpxPulseActionResponse,
  type HpxPulseResponse,
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
  auto_restart_interval_minutes: z.coerce.number().int().min(0).max(10080),
})

type FormValues = z.infer<typeof schema>

const AUTO_RESTART_PRESETS = [
  { value: 0, labelKey: 'hpxPulse.autoRestartOff', defaultValue: 'Off' },
  { value: 15, labelKey: 'hpxPulse.autoRestart15m', defaultValue: 'Every 15 min' },
  { value: 30, labelKey: 'hpxPulse.autoRestart30m', defaultValue: 'Every 30 min' },
  { value: 60, labelKey: 'hpxPulse.autoRestart1h', defaultValue: 'Every 1 hour' },
  { value: 360, labelKey: 'hpxPulse.autoRestart6h', defaultValue: 'Every 6 hours' },
  { value: 720, labelKey: 'hpxPulse.autoRestart12h', defaultValue: 'Every 12 hours' },
  { value: 1440, labelKey: 'hpxPulse.autoRestart24h', defaultValue: 'Every 24 hours' },
] as const

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
  editingPulse?: HpxPulseResponse | null
}

function pulseToFormValues(pulse: HpxPulseResponse): FormValues {
  const portForwards = (pulse.port_forwards ?? [])
    .map(fromTunnelPortString)
    .filter((row): row is NonNullable<typeof row> => row != null)
  return {
    name: pulse.name,
    iran_public_ip: pulse.iran_public_ip,
    abroad_public_ip: pulse.abroad_public_ip,
    goal: pulse.goal,
    control_port: pulse.control_port,
    port_forwards: portForwards.length ? portForwards : [{ external_port: 443, internal_ip: '', internal_port: 443 }],
    auto_restart_interval_minutes: pulse.auto_restart_interval_minutes ?? 0,
  }
}

export default function HpxPulseWizard({ open, onOpenChange, onCreated, editingPulse }: Props) {
  const { t, i18n } = useTranslation()
  const dir = useDirDetection()
  const fa = i18n.language?.startsWith('fa')
  const handleError = useDynamicErrorHandler()
  const adviseMutation = useAdvisePulse()
  const createMutation = useCreateHpxPulse()
  const updateMutation = useUpdateHpxPulse()
  const isEditing = !!editingPulse
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
      auto_restart_interval_minutes: 0,
    },
  })

  useEffect(() => {
    if (!open) return
    if (editingPulse) {
      form.reset(pulseToFormValues(editingPulse))
      setAdvice(editingPulse.advice)
      setSelectedProfile(editingPulse.profile_id)
      return
    }
    form.reset({
      name: defaultPulseName(),
      iran_public_ip: '',
      abroad_public_ip: '',
      goal: 'balanced',
      control_port: randomTunnelPort(),
      port_forwards: [{ external_port: 443, internal_ip: '', internal_port: 443 }],
      auto_restart_interval_minutes: 0,
    })
    setAdvice(null)
    setSelectedProfile(null)
  }, [open, editingPulse, form])

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

  const submit = async (values: FormValues) => {
    try {
      let profileId = selectedProfile ?? advice?.recommended_profile_id
      if (!profileId) {
        const res = await runAdvise(values)
        profileId = res.recommended_profile_id
      }

      const portForwards = (values.port_forwards ?? []).map(toTunnelPortString)
      const autoRestart = values.auto_restart_interval_minutes > 0 ? values.auto_restart_interval_minutes : 0

      if (isEditing && editingPulse) {
        await updateMutation.mutateAsync({
          id: editingPulse.id,
          data: {
            name: values.name.trim(),
            iran_public_ip: values.iran_public_ip.trim(),
            abroad_public_ip: values.abroad_public_ip.trim(),
            goal: values.goal,
            profile_id: profileId,
            control_port: values.control_port,
            port_forwards: portForwards,
            auto_restart_interval_minutes: autoRestart,
          },
        })
        toast.success(t('hpxPulse.updateSuccess', { defaultValue: 'Pulse updated — agents will sync' }))
        onOpenChange(false)
        return
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
        port_forwards: portForwards,
        auto_restart_interval_minutes: autoRestart || null,
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
          <DialogTitle>
            {isEditing
              ? t('hpxPulse.editTitle', { defaultValue: 'Edit Pulse' })
              : t('hpxPulse.wizard.title', { defaultValue: 'HPX Pulse Advisor' })}
          </DialogTitle>
          <DialogDescription>
            {isEditing
              ? t('hpxPulse.editDescription', { defaultValue: 'Update tunnel settings — connected agents will restart and sync.' })
              : t('hpxPulse.wizard.description', {
                  defaultValue: 'Enter host facts, get ranked HPX Reverse/Direct profiles, then deploy Iran and abroad agents.',
                })}
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(submit)} className="space-y-4">
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
              <FormField
                control={form.control}
                name="auto_restart_interval_minutes"
                render={({ field }) => {
                  const presetValues = AUTO_RESTART_PRESETS.map(p => p.value)
                  const isCustom = !presetValues.includes(Number(field.value) as (typeof presetValues)[number])
                  const selectValue = isCustom ? 'custom' : String(field.value ?? 0)
                  return (
                    <FormItem>
                      <FormLabel>{t('hpxPulse.autoRestart', { defaultValue: 'Auto-restart' })}</FormLabel>
                      <Select
                        value={selectValue}
                        onValueChange={value => {
                          if (value === 'custom') {
                            field.onChange(field.value && !presetValues.includes(Number(field.value) as never) ? field.value : 45)
                            return
                          }
                          field.onChange(Number(value))
                        }}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {AUTO_RESTART_PRESETS.map(preset => (
                            <SelectItem key={preset.value} value={String(preset.value)}>
                              {t(preset.labelKey, { defaultValue: preset.defaultValue })}
                            </SelectItem>
                          ))}
                          <SelectItem value="custom">
                            {t('hpxPulse.autoRestartCustom', { defaultValue: 'Custom minutes…' })}
                          </SelectItem>
                        </SelectContent>
                      </Select>
                      {isCustom && (
                        <Input
                          type="number"
                          min={1}
                          max={10080}
                          dir="ltr"
                          className="mt-2"
                          value={field.value || ''}
                          onChange={e => field.onChange(Number(e.target.value) || 0)}
                          placeholder="45"
                        />
                      )}
                      <p className="text-muted-foreground text-xs">
                        {t('hpxPulse.autoRestartHint', {
                          defaultValue: 'Panel will queue a tunnel restart on this schedule. Agents pick it up within ~30s.',
                        })}
                      </p>
                      <FormMessage />
                    </FormItem>
                  )
                }}
              />
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
              <LoaderButton
                type="submit"
                loading={createMutation.isPending || updateMutation.isPending || adviseMutation.isPending}
              >
                {isEditing
                  ? t('save', { defaultValue: 'Save' })
                  : t('hpxPulse.create', { defaultValue: 'Create Pulse' })}
              </LoaderButton>
            </div>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
