import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { LoaderButton } from '@/components/ui/loader-button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import useDirDetection from '@/hooks/use-dir-detection'
import useDynamicErrorHandler from '@/hooks/use-dynamic-errors'
import { cn } from '@/lib/utils'
import { DirectSpoofGuide } from '@/features/hpx-pulse/components/direct-spoof-guide'
import { toTunnelPortString, fromTunnelPortString } from '@/features/hpx-pulse/utils/port-forwards'
import { RankedTunnelPresets } from '@/features/hpx-pulse/wizard/ranked-tunnel-presets'
import {
  useAdvisePulse,
  useCreateHpxPulse,
  useUpdateHpxPulse,
  type HpxPulseActionResponse,
  type HpxPulseResponse,
  type PulseAdviseResponse,
  type PulseSpoofConfig,
  type PulseSpoofProfile,
} from '@/service/api/hpx-pulse'
import { zodResolver } from '@hookform/resolvers/zod'
import { Dices, Sparkles, Trash2 } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { z } from 'zod'

const portForwardSchema = z.object({
  external_port: z.coerce.number().int().min(1).max(65535),
  internal_ip: z.string().max(45).optional().default(''),
  internal_port: z.coerce.number().int().min(1).max(65535),
})

const spoofProfileSchema = z.enum(['udp', 'icmp', 'tcp', 'icmpv6', 'proto58', 'ipip', 'gre'])

const schema = z.object({
  name: z.string().min(1, 'Name required').max(40),
  iran_public_ip: z.string().min(7, 'Iran IP required'),
  abroad_public_ip: z.string().min(7, 'Abroad IP required'),
  goal: z.enum(['mobile', 'hard', 'fast', 'stealth', 'balanced', 'speed', 'spoof']),
  control_port: z.coerce.number().int().min(1024).max(65535),
  port_forwards: z.array(portForwardSchema).default([]),
  auto_restart_interval_minutes: z.coerce.number().int().min(0).max(10080),
  auto_heal_enabled: z.boolean().default(true),
  backup_pulse_id: z.coerce.number().int().min(0).optional(),
  auto_failover: z.boolean().default(false),
  auto_failback: z.boolean().default(true),
  priority: z.coerce.number().int().min(0).max(100).default(0),
  spoof_profile: spoofProfileSchema.default('udp'),
  spoof_stealth: z.boolean().default(false),
  spoof_src_ip: z.string().max(45).optional().default(''),
  spoof_mtu: z.coerce.number().int().min(0).max(9000).default(0),
  spoof_sockbuf: z.coerce.number().int().min(0).max(268435456).default(0),
})

function isSpoofProfileId(profileId: string | null | undefined) {
  return !!profileId && profileId.startsWith('pulse-direct-spoof')
}

function spoofConfigFromForm(values: FormValues): PulseSpoofConfig {
  return {
    profile: values.spoof_profile as PulseSpoofProfile,
    stealth: values.spoof_stealth,
    src_ip: (values.spoof_src_ip || '').trim(),
    src_pool: [],
    iran_src_ip: '',
    abroad_src_ip: '',
    mtu: values.spoof_mtu || 0,
    sockbuf: values.spoof_sockbuf || 0,
    icmp_reply: false,
  }
}

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
  /** Called after an edit is saved (the response carries new join commands when agents must rejoin). */
  onUpdated?: (res: HpxPulseActionResponse) => void
  editingPulse?: HpxPulseResponse | null
}

function pulseToFormValues(pulse: HpxPulseResponse): FormValues {
  const portForwards = (pulse.port_forwards ?? [])
    .map(fromTunnelPortString)
    .filter((row): row is NonNullable<typeof row> => row != null)
  const spoof = pulse.spoof_config
  return {
    name: pulse.name,
    iran_public_ip: pulse.iran_public_ip,
    abroad_public_ip: pulse.abroad_public_ip,
    goal: pulse.goal === 'spoof' || pulse.carrier === 'spoof' ? 'spoof' : pulse.goal,
    control_port: pulse.control_port,
    port_forwards: portForwards.length ? portForwards : [{ external_port: 443, internal_ip: '', internal_port: 443 }],
    auto_restart_interval_minutes: pulse.auto_restart_interval_minutes ?? 0,
    auto_heal_enabled: pulse.auto_heal_enabled ?? true,
    backup_pulse_id: pulse.backup_pulse_id ?? 0,
    auto_failover: pulse.auto_failover ?? false,
    auto_failback: pulse.auto_failback ?? true,
    priority: pulse.priority ?? 0,
    spoof_profile: (spoof?.profile as PulseSpoofProfile) || 'udp',
    spoof_stealth: spoof?.stealth ?? false,
    spoof_src_ip: spoof?.src_ip || '',
    spoof_mtu: spoof?.mtu ?? 0,
    spoof_sockbuf: spoof?.sockbuf ?? 0,
  }
}

export default function HpxPulseWizard({ open, onOpenChange, onCreated, onUpdated, editingPulse }: Props) {
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
      goal: 'mobile',
      control_port: randomTunnelPort(),
      port_forwards: [{ external_port: 443, internal_ip: '', internal_port: 443 }],
      auto_restart_interval_minutes: 0,
      auto_heal_enabled: true,
      backup_pulse_id: 0,
      auto_failover: false,
      auto_failback: true,
      priority: 0,
      spoof_profile: 'udp',
      spoof_stealth: false,
      spoof_src_ip: '',
      spoof_mtu: 0,
      spoof_sockbuf: 0,
    },
  })

  // The list re-fetches in the background and hands us a fresh object every time. Resetting the
  // form on object identity wiped what the admin was typing (IPs "reverting"), so only reset when
  // the dialog opens or a different pulse is being edited, using the latest DB snapshot.
  const editingPulseRef = useRef<HpxPulseResponse | null | undefined>(editingPulse)
  editingPulseRef.current = editingPulse
  const editingId = editingPulse?.id ?? null

  useEffect(() => {
    if (!open) return
    const current = editingPulseRef.current
    if (current) {
      form.reset(pulseToFormValues(current))
      setAdvice(current.advice)
      setSelectedProfile(current.profile_id)
      return
    }
    form.reset({
      name: defaultPulseName(),
      iran_public_ip: '',
      abroad_public_ip: '',
      goal: 'mobile',
      control_port: randomTunnelPort(),
      port_forwards: [{ external_port: 443, internal_ip: '', internal_port: 443 }],
      auto_restart_interval_minutes: 0,
      auto_heal_enabled: true,
      backup_pulse_id: 0,
      auto_failover: false,
      auto_failback: true,
      priority: 0,
      spoof_profile: 'udp',
      spoof_stealth: false,
      spoof_src_ip: '',
      spoof_mtu: 0,
      spoof_sockbuf: 0,
    })
    setAdvice(null)
    setSelectedProfile(null)
  }, [open, editingId, form])

  const watchedGoal = form.watch('goal')
  const showSpoofPanel = useMemo(
    () => watchedGoal === 'spoof' || isSpoofProfileId(selectedProfile),
    [watchedGoal, selectedProfile],
  )

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

      const includeSpoof = values.goal === 'spoof' || isSpoofProfileId(profileId)
      const spoofPayload = includeSpoof ? spoofConfigFromForm(values) : undefined

      if (isEditing && editingPulse) {
        const updated = await updateMutation.mutateAsync({
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
            auto_heal_enabled: values.auto_heal_enabled,
            backup_pulse_id: values.backup_pulse_id && values.backup_pulse_id > 0 ? values.backup_pulse_id : null,
            auto_failover: values.auto_failover,
            auto_failback: values.auto_failback,
            priority: values.priority,
            ...(includeSpoof
              ? { spoof_config: spoofPayload }
              : editingPulse.carrier === 'spoof'
                ? { spoof_config: null }
                : {}),
          },
        })
        const mustRejoin = Boolean(updated?.iran_join_command || updated?.abroad_join_command)
        if (mustRejoin) {
          toast.warning(
            t('hpxPulse.updateRejoin', {
              defaultValue: 'IP/config changed — agents are disconnecting. Reconnect both servers with the new join tokens.',
            }),
            { duration: 10000 },
          )
        } else {
          toast.success(t('hpxPulse.updateSuccess', { defaultValue: 'Pulse updated — agents will sync' }))
        }
        // Hand the response (join commands) to the list instead of just closing, then re-read the DB.
        onUpdated?.(updated)
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
        auto_heal_enabled: values.auto_heal_enabled,
        backup_pulse_id: values.backup_pulse_id && values.backup_pulse_id > 0 ? values.backup_pulse_id : null,
        auto_failover: values.auto_failover,
        auto_failback: values.auto_failback,
        priority: values.priority,
        ...(includeSpoof ? { spoof_config: spoofPayload } : {}),
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
                  <FormLabel>{t('hpxPulse.intent', { defaultValue: 'Intent' })}</FormLabel>
                  <Select onValueChange={v => { field.onChange(v); setAdvice(null) }} value={field.value}>
                    <FormControl><SelectTrigger><SelectValue /></SelectTrigger></FormControl>
                    <SelectContent>
                      <SelectItem value="mobile">{t('hpxPulse.intentMobile', { defaultValue: 'Mobile — stealth + balance' })}</SelectItem>
                      <SelectItem value="hard">{t('hpxPulse.intentHard', { defaultValue: 'Hard — aggressive stealth' })}</SelectItem>
                      <SelectItem value="fast">{t('hpxPulse.intentFast', { defaultValue: 'Fast — turbo / KCP / QUIC' })}</SelectItem>
                      <SelectItem value="spoof">{t('hpxPulse.intentSpoof', { defaultValue: 'Direct Spoof — forged source L3' })}</SelectItem>
                      <SelectItem value="stealth">stealth</SelectItem>
                      <SelectItem value="balanced">balanced</SelectItem>
                      <SelectItem value="speed">speed</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-muted-foreground text-xs">
                    {watchedGoal === 'spoof'
                      ? t('hpxPulse.intentSpoofHint', {
                          defaultValue:
                            'Direct Spoof only — ranks UDP/ICMP/Stealth spoof profiles. Reverse cannot use this carrier.',
                        })
                      : t('hpxPulse.intentHint', {
                          defaultValue:
                            'Hard/Mobile rank TCP Stealth & WSS. Fast ranks KCP / QUIC / UDP turbo tunnels — then preview again.',
                        })}
                  </p>
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

            <div className="grid gap-3 rounded-lg border p-3 sm:grid-cols-2">
              <p className="text-sm font-medium sm:col-span-2">
                {t('hpxPulse.failoverSection', { defaultValue: 'Path failover' })}
              </p>
              <FormField control={form.control} name="backup_pulse_id" render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('hpxPulse.backupPulseId', { defaultValue: 'Backup pulse ID' })}</FormLabel>
                  <FormControl>
                    <Input
                      type="number"
                      dir="ltr"
                      min={0}
                      {...field}
                      value={field.value || ''}
                      onChange={e => field.onChange(Number(e.target.value) || 0)}
                      placeholder="0 = none"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )} />
              <FormField control={form.control} name="priority" render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('hpxPulse.priority', { defaultValue: 'Priority' })}</FormLabel>
                  <FormControl><Input type="number" dir="ltr" min={0} max={100} {...field} /></FormControl>
                </FormItem>
              )} />
              <FormField control={form.control} name="auto_failover" render={({ field }) => (
                <FormItem className="flex items-center gap-2 space-y-0">
                  <FormControl>
                    <input type="checkbox" className="size-4" checked={field.value} onChange={e => field.onChange(e.target.checked)} />
                  </FormControl>
                  <FormLabel>{t('hpxPulse.autoFailover', { defaultValue: 'Auto-failover to backup' })}</FormLabel>
                </FormItem>
              )} />
              <FormField control={form.control} name="auto_failback" render={({ field }) => (
                <FormItem className="flex items-center gap-2 space-y-0">
                  <FormControl>
                    <input type="checkbox" className="size-4" checked={field.value} onChange={e => field.onChange(e.target.checked)} />
                  </FormControl>
                  <FormLabel>{t('hpxPulse.autoFailback', { defaultValue: 'Auto-failback when primary recovers' })}</FormLabel>
                </FormItem>
              )} />
              <FormField control={form.control} name="auto_heal_enabled" render={({ field }) => (
                <FormItem className="flex items-center gap-2 space-y-0 sm:col-span-2">
                  <FormControl>
                    <input type="checkbox" className="size-4" checked={field.value} onChange={e => field.onChange(e.target.checked)} />
                  </FormControl>
                  <FormLabel>{t('hpxPulse.autoHeal', { defaultValue: 'Auto-heal stale agents' })}</FormLabel>
                </FormItem>
              )} />
            </div>

            {showSpoofPanel && (
              <>
                <div className="space-y-3 rounded-lg border border-emerald-500/25 bg-emerald-500/5 p-3">
                  <div>
                    <p className="text-sm font-medium">
                      {t('hpxPulse.spoofSection', { defaultValue: 'Direct Spoof settings' })}
                    </p>
                    <p className="text-muted-foreground mt-0.5 text-xs">
                      {t('hpxPulse.spoofSectionHint', {
                        defaultValue:
                          'Direct L3 only — Reverse cannot carry spoof. Leave forged source empty on first run.',
                      })}
                    </p>
                  </div>
                  <div className="grid gap-3 sm:grid-cols-2">
                    <FormField
                      control={form.control}
                      name="spoof_profile"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>{t('hpxPulse.spoofProfile', { defaultValue: 'Packet profile' })}</FormLabel>
                          <Select onValueChange={field.onChange} value={field.value}>
                            <FormControl>
                              <SelectTrigger className="cursor-pointer">
                                <SelectValue />
                              </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                              <SelectItem value="udp">udp (recommended)</SelectItem>
                              <SelectItem value="icmp">icmp</SelectItem>
                              <SelectItem value="tcp">tcp</SelectItem>
                              <SelectItem value="icmpv6">icmpv6</SelectItem>
                              <SelectItem value="proto58">proto58</SelectItem>
                              <SelectItem value="ipip">ipip</SelectItem>
                              <SelectItem value="gre">gre</SelectItem>
                            </SelectContent>
                          </Select>
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="spoof_stealth"
                      render={({ field }) => (
                        <FormItem className="flex flex-col justify-end gap-2 space-y-0">
                          <FormLabel>{t('hpxPulse.spoofStealth', { defaultValue: 'Stealth bundle' })}</FormLabel>
                          <div className="flex h-9 items-center gap-2">
                            <FormControl>
                              <Switch
                                checked={field.value}
                                onCheckedChange={field.onChange}
                                className="cursor-pointer"
                              />
                            </FormControl>
                            <span className="text-muted-foreground text-xs">
                              {t('hpxPulse.spoofStealthHint', {
                                defaultValue: 'Padding + TTL/DSCP + port shuffle (both ends)',
                              })}
                            </span>
                          </div>
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="spoof_src_ip"
                      render={({ field }) => (
                        <FormItem className="sm:col-span-2">
                          <FormLabel>{t('hpxPulse.spoofSrcIp', { defaultValue: 'Forged source IP (optional)' })}</FormLabel>
                          <FormControl>
                            <Input {...field} dir="ltr" placeholder={fa ? 'خالی = بدون جعل (اولین اجرا)' : 'empty = no forge (first run)'} />
                          </FormControl>
                          <p className="text-muted-foreground text-xs">
                            {t('hpxPulse.spoofSrcIpHint', {
                              defaultValue: 'Only set an address the path actually delivers. Iran spoof_peer_ip is autofilled from Abroad IP.',
                            })}
                          </p>
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="spoof_mtu"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>{t('hpxPulse.spoofMtu', { defaultValue: 'spoof_mtu (0=default)' })}</FormLabel>
                          <FormControl>
                            <Input type="number" {...field} dir="ltr" />
                          </FormControl>
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="spoof_sockbuf"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>{t('hpxPulse.spoofSockbuf', { defaultValue: 'spoof_sockbuf (0=4MiB)' })}</FormLabel>
                          <FormControl>
                            <Input type="number" {...field} dir="ltr" />
                          </FormControl>
                        </FormItem>
                      )}
                    />
                  </div>
                </div>
                <DirectSpoofGuide fa={fa} />
              </>
            )}

            <Button
              type="button"
              variant="secondary"
              onClick={previewAdvise}
              disabled={adviseMutation.isPending}
              className="border-primary/20 bg-primary/10 hover:bg-primary/15 text-foreground cursor-pointer"
            >
              <Sparkles className="size-4 text-primary" />
              {t('hpxPulse.advise', { defaultValue: 'Preview ranked tunnels' })}
            </Button>

            {advice && (
              <RankedTunnelPresets
                profiles={advice.profiles}
                recommendedId={advice.recommended_profile_id}
                selectedId={selectedProfile}
                onSelect={id => {
                  setSelectedProfile(id)
                  if (id === 'pulse-direct-spoof-udp') {
                    form.setValue('spoof_profile', 'udp')
                    form.setValue('spoof_stealth', false)
                  } else if (id === 'pulse-direct-spoof-icmp') {
                    form.setValue('spoof_profile', 'icmp')
                    form.setValue('spoof_stealth', false)
                  } else if (id === 'pulse-direct-spoof-stealth') {
                    form.setValue('spoof_profile', 'udp')
                    form.setValue('spoof_stealth', true)
                  }
                }}
                fa={fa}
              />
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
