import { Button } from '@/components/ui/button'
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { LoaderButton } from '@/components/ui/loader-button'
import { PasswordInput } from '@/components/ui/password-input'
import { Skeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import { cn } from '@/lib/utils'
import { getGetSettingsQueryKey, useGetSettings, useGetWorkersHealth, useModifySettings } from '@/service/api'
import { zodResolver } from '@hookform/resolvers/zod'
import { useQueryClient } from '@tanstack/react-query'
import {
  Activity,
  Bot,
  CheckCircle2,
  Globe,
  MessageCircle,
  Radio,
  RefreshCcw,
  Shield,
  Smartphone,
  Users,
  XCircle,
} from 'lucide-react'
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { z } from 'zod'

const schema = z.object({
  enable: z.boolean().default(false),
  token: z.string().optional(),
  proxy_url: z.string().url('Please enter a valid URL').optional().or(z.literal('')),
  mini_app_login: z.boolean().default(false),
  mini_app_url: z.string().url('Please enter a valid URL').optional().or(z.literal('')),
  panel_url: z.string().url('Please enter a valid URL').optional().or(z.literal('')),
  for_admins_only: z.boolean().default(true),
})

type FormInput = z.input<typeof schema>

function currentPanelUrl() {
  return `${window.location.protocol}//${window.location.host}`
}

function mapPayload(data: FormInput) {
  const mapped = {
    ...data,
    enable: data.enable ?? false,
    method: 'long-polling' as const,
    mini_app_login: data.mini_app_login ?? false,
    for_admins_only: data.for_admins_only ?? true,
    token: data.token?.trim() || undefined,
    proxy_url: data.proxy_url?.trim() || undefined,
    mini_app_web_url: data.mini_app_url?.trim() || undefined,
    panel_url: data.panel_url?.trim() || undefined,
  }
  delete (mapped as { mini_app_url?: string }).mini_app_url
  return { telegram: mapped }
}

function StatusPill({
  ok,
  label,
  detail,
}: {
  ok: boolean
  label: string
  detail: string
}) {
  return (
    <div
      className={cn(
        'flex min-w-0 flex-1 items-start gap-3 rounded-xl border px-3 py-3 transition-colors duration-200',
        ok
          ? 'border-emerald-500/30 bg-emerald-500/10'
          : 'border-border/70 bg-muted/30',
      )}
    >
      {ok ? (
        <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-500" aria-hidden />
      ) : (
        <XCircle className="text-muted-foreground mt-0.5 size-4 shrink-0" aria-hidden />
      )}
      <div className="min-w-0">
        <p className="text-sm font-medium tracking-tight">{label}</p>
        <p className="text-muted-foreground mt-0.5 text-xs leading-relaxed">{detail}</p>
      </div>
    </div>
  )
}

export function TelegramBotHub() {
  const { t, i18n } = useTranslation()
  const fa = i18n.language?.startsWith('fa')
  const queryClient = useQueryClient()

  const { data: settings, isLoading, error } = useGetSettings()
  const { mutateAsync: modifySettings, isPending: isSaving } = useModifySettings()
  const { data: workersHealth } = useGetWorkersHealth({
    query: { retry: false, refetchInterval: 30000, staleTime: 30000 },
  })

  const form = useForm<FormInput>({
    resolver: zodResolver(schema),
    defaultValues: {
      enable: false,
      token: '',
      proxy_url: '',
      mini_app_login: false,
      mini_app_url: '',
      panel_url: '',
      for_admins_only: true,
    },
  })

  const enableTelegram = form.watch('enable')
  const tokenValue = form.watch('token')
  const panelUrl = form.watch('panel_url')
  const miniAppLogin = form.watch('mini_app_login')
  const forAdminsOnly = form.watch('for_admins_only')

  const schedulerStatus = workersHealth?.scheduler?.status?.toLowerCase().trim()
  const nodeStatus = workersHealth?.node?.status?.toLowerCase().trim()
  const isMultiWorkerMode = !!workersHealth && !(schedulerStatus === 'disabled' && nodeStatus === 'disabled')

  const botArmed = !!enableTelegram && !!tokenValue?.trim()
  const reachReady = !!panelUrl?.trim()

  useEffect(() => {
    if (!settings?.telegram) return
    const tg = settings.telegram
    form.reset({
      enable: tg.enable || false,
      token: tg.token || '',
      proxy_url: tg.proxy_url || '',
      mini_app_login: tg.mini_app_login || false,
      mini_app_url: tg.mini_app_web_url || '',
      panel_url: tg.panel_url || '',
      for_admins_only: tg.for_admins_only !== undefined ? tg.for_admins_only : true,
    })
  }, [settings, form])

  const onSubmit = async (data: FormInput) => {
    try {
      const updated = await modifySettings({ data: mapPayload(data) })
      queryClient.setQueryData(getGetSettingsQueryKey(), updated)
      queryClient.invalidateQueries({ queryKey: ['/api/settings'] })
      toast.success(t('telegramBot.saveSuccess', { defaultValue: 'Telegram bot settings saved' }))
    } catch (err: any) {
      const detail = err?.data?.detail || err?.message
      toast.error(t('telegramBot.saveFailed', { defaultValue: 'Failed to save Telegram bot settings' }), {
        description: typeof detail === 'string' ? detail : undefined,
      })
    }
  }

  const handleCancel = () => {
    if (!settings?.telegram) return
    const tg = settings.telegram
    form.reset({
      enable: tg.enable || false,
      token: tg.token || '',
      proxy_url: tg.proxy_url || '',
      mini_app_login: tg.mini_app_login || false,
      mini_app_url: tg.mini_app_web_url || '',
      panel_url: tg.panel_url || '',
      for_admins_only: tg.for_admins_only !== undefined ? tg.for_admins_only : true,
    })
    toast.success(t('telegramBot.cancelSuccess', { defaultValue: 'Changes discarded' }))
  }

  if (isLoading) {
    return (
      <div className="space-y-4 p-4 sm:p-6">
        <Skeleton className="h-28 w-full rounded-2xl" />
        <div className="grid gap-4 lg:grid-cols-2">
          <Skeleton className="h-64 rounded-2xl" />
          <Skeleton className="h-64 rounded-2xl" />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex min-h-[320px] items-center justify-center p-6">
        <div className="max-w-md space-y-2 text-center">
          <XCircle className="text-destructive mx-auto size-8" />
          <p className="text-destructive text-sm font-medium">
            {t('telegramBot.loadError', { defaultValue: 'Could not load Telegram bot settings' })}
          </p>
        </div>
      </div>
    )
  }

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        className="relative mx-auto flex w-full max-w-6xl flex-col gap-5 px-3 pb-28 pt-2 sm:px-5 sm:pt-4 md:px-6"
        dir={fa ? 'rtl' : 'ltr'}
      >
        {/* Hero / ops strip */}
        <section className="relative overflow-hidden rounded-2xl border border-sky-500/20 bg-gradient-to-br from-sky-500/10 via-card/80 to-card p-4 sm:p-6">
          <div className="pointer-events-none absolute -top-20 -right-16 size-56 rounded-full bg-sky-500/15 blur-3xl" aria-hidden />
          <div className="pointer-events-none absolute -bottom-24 -left-10 size-48 rounded-full bg-emerald-500/10 blur-3xl" aria-hidden />

          <div className="relative flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0 space-y-2">
              <div className="flex items-center gap-2">
                <span className="inline-flex size-9 items-center justify-center rounded-xl border border-sky-500/30 bg-sky-500/15 text-sky-400">
                  <MessageCircle className="size-4" aria-hidden />
                </span>
                <div>
                  <p className="text-sky-400/90 text-[10px] font-semibold tracking-[0.16em] uppercase">
                    {t('telegramBot.sector', { defaultValue: 'Messaging' })}
                  </p>
                  <h2 className="font-display text-lg font-bold tracking-tight sm:text-xl">
                    {t('telegramBot.heroTitle', { defaultValue: 'Telegram Bot Control' })}
                  </h2>
                </div>
              </div>
              <p className="text-muted-foreground max-w-2xl text-xs leading-relaxed sm:text-sm">
                {t('telegramBot.heroDescription', {
                  defaultValue:
                    'Stand-alone bot console — long-polling link to Telegram for shop, users, and admin alerts. Not buried under Settings.',
                })}
              </p>
            </div>

            <div
              className={cn(
                'inline-flex shrink-0 items-center gap-2 self-start rounded-full border px-3 py-1.5 text-xs font-medium',
                botArmed
                  ? 'border-emerald-500/40 bg-emerald-500/15 text-emerald-400'
                  : 'border-border bg-muted/40 text-muted-foreground',
              )}
            >
              <span className={cn('size-1.5 rounded-full', botArmed ? 'bg-emerald-400' : 'bg-muted-foreground')} />
              {botArmed
                ? t('telegramBot.statusArmed', { defaultValue: 'Bot armed' })
                : t('telegramBot.statusIdle', { defaultValue: 'Bot idle' })}
            </div>
          </div>

          <div className="relative mt-4 grid gap-2 sm:grid-cols-3">
            <StatusPill
              ok={botArmed}
              label={t('telegramBot.chipConnection', { defaultValue: 'Connection' })}
              detail={
                botArmed
                  ? t('telegramBot.chipConnectionOn', { defaultValue: 'Enabled with token' })
                  : t('telegramBot.chipConnectionOff', { defaultValue: 'Enable + token required' })
              }
            />
            <StatusPill
              ok={reachReady}
              label={t('telegramBot.chipPanelUrl', { defaultValue: 'Panel URL' })}
              detail={
                reachReady
                  ? t('telegramBot.chipPanelUrlOn', { defaultValue: 'Public URL set for sub links' })
                  : t('telegramBot.chipPanelUrlOff', { defaultValue: 'Needed for long polling' })
              }
            />
            <StatusPill
              ok={!isMultiWorkerMode}
              label={t('telegramBot.chipWorkers', { defaultValue: 'Workers' })}
              detail={
                isMultiWorkerMode
                  ? t('telegramBot.chipWorkersWarn', { defaultValue: 'Multi-worker blocks long polling' })
                  : t('telegramBot.chipWorkersOk', { defaultValue: 'Single-worker friendly' })
              }
            />
          </div>

          {enableTelegram && isMultiWorkerMode && (
            <div className="relative mt-3 flex items-start gap-2 rounded-xl border border-amber-500/35 bg-amber-500/10 px-3 py-2.5 text-xs text-amber-800 dark:text-amber-200">
              <Activity className="mt-0.5 size-3.5 shrink-0" aria-hidden />
              <p>
                {t('telegramBot.multiWorkerWarn', {
                  defaultValue: 'Long polling is disabled in multi-worker mode. Disable NATS and set UVICORN_WORKERS=1.',
                })}
              </p>
            </div>
          )}
        </section>

        <div className="grid gap-4 lg:grid-cols-2">
          {/* Connection */}
          <section className="space-y-4 rounded-2xl border border-border/80 bg-card/60 p-4 shadow-sm backdrop-blur-sm sm:p-5">
            <div className="flex items-center gap-2">
              <Radio className="size-4 text-sky-400" aria-hidden />
              <div>
                <h3 className="text-sm font-semibold tracking-tight">
                  {t('telegramBot.connectionTitle', { defaultValue: 'Connection' })}
                </h3>
                <p className="text-muted-foreground text-xs">
                  {t('telegramBot.connectionHint', { defaultValue: 'Token from @BotFather · long polling only' })}
                </p>
              </div>
            </div>

            <FormField
              control={form.control}
              name="enable"
              render={({ field }) => (
                <FormItem className="hover:bg-accent/40 flex flex-row items-center justify-between gap-3 rounded-xl border border-border/60 bg-background/40 p-3 transition-colors duration-200">
                  <div className="space-y-0.5">
                    <FormLabel className="flex cursor-pointer items-center gap-2 text-sm font-medium">
                      <Bot className="size-4" />
                      {t('settings.telegram.general.enable')}
                    </FormLabel>
                    <FormDescription className="text-xs">{t('settings.telegram.general.enableDescription')}</FormDescription>
                  </div>
                  <FormControl>
                    <Switch checked={field.value} onCheckedChange={field.onChange} className="cursor-pointer" />
                  </FormControl>
                </FormItem>
              )}
            />

            {enableTelegram && (
              <div className="space-y-3">
                <FormField
                  control={form.control}
                  name="token"
                  render={({ field }) => (
                    <FormItem className="space-y-2">
                      <FormLabel className="flex items-center gap-2 text-xs font-medium sm:text-sm">
                        <Bot className="size-3.5" />
                        {t('settings.telegram.general.token')}
                      </FormLabel>
                      <FormControl>
                        <PasswordInput
                          placeholder={t('settings.telegram.general.tokenPlaceholder')}
                          {...field}
                          className="font-mono text-xs sm:text-sm"
                          dir="ltr"
                        />
                      </FormControl>
                      <FormDescription className="text-xs">{t('settings.telegram.general.tokenDescription')}</FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            )}
          </section>

          {/* Reachability */}
          <section className="space-y-4 rounded-2xl border border-border/80 bg-card/60 p-4 shadow-sm backdrop-blur-sm sm:p-5">
            <div className="flex items-center gap-2">
              <Globe className="size-4 text-emerald-400" aria-hidden />
              <div>
                <h3 className="text-sm font-semibold tracking-tight">
                  {t('telegramBot.reachTitle', { defaultValue: 'Reachability' })}
                </h3>
                <p className="text-muted-foreground text-xs">
                  {t('telegramBot.reachHint', { defaultValue: 'Public panel URL for sub links · optional proxy' })}
                </p>
              </div>
            </div>

            {enableTelegram ? (
              <div className="space-y-3">
                <FormField
                  control={form.control}
                  name="panel_url"
                  render={({ field }) => (
                    <FormItem className="space-y-2">
                      <FormLabel className="flex items-center gap-2 text-xs font-medium sm:text-sm">
                        <Globe className="size-3.5" />
                        {t('settings.telegram.general.panelUrl')}
                      </FormLabel>
                      <div className="relative">
                        <FormControl>
                          <Input
                            type="url"
                            placeholder={t('settings.telegram.general.panelUrlPlaceholder')}
                            {...field}
                            className="pe-10 font-mono text-xs sm:text-sm"
                            dir="ltr"
                          />
                        </FormControl>
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon"
                          className="absolute end-1 top-1/2 size-8 -translate-y-1/2 cursor-pointer"
                          onClick={e => {
                            e.preventDefault()
                            field.onChange(currentPanelUrl())
                            toast.success(t('settings.telegram.general.panelUrlApplied'))
                          }}
                        >
                          <RefreshCcw className="size-3.5" />
                        </Button>
                      </div>
                      <FormDescription className="text-xs">{t('settings.telegram.general.panelUrlDescription')}</FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="proxy_url"
                  render={({ field }) => (
                    <FormItem className="space-y-2">
                      <FormLabel className="flex items-center gap-2 text-xs font-medium sm:text-sm">
                        <Globe className="size-3.5" />
                        {t('settings.telegram.general.proxyUrl')}
                      </FormLabel>
                      <FormControl>
                        <Input
                          type="url"
                          placeholder={t('settings.telegram.general.proxyUrlPlaceholder')}
                          {...field}
                          className="font-mono text-xs sm:text-sm"
                          dir="ltr"
                        />
                      </FormControl>
                      <FormDescription className="text-xs">{t('settings.telegram.general.proxyUrlDescription')}</FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            ) : (
              <p className="text-muted-foreground rounded-xl border border-dashed border-border/70 px-3 py-8 text-center text-xs">
                {t('telegramBot.enableFirst', { defaultValue: 'Turn the bot on to configure reachability.' })}
              </p>
            )}
          </section>

          {/* Access */}
          <section className="space-y-4 rounded-2xl border border-border/80 bg-card/60 p-4 shadow-sm backdrop-blur-sm sm:p-5 lg:col-span-2">
            <div className="flex items-center gap-2">
              <Shield className="size-4 text-amber-400" aria-hidden />
              <div>
                <h3 className="text-sm font-semibold tracking-tight">
                  {t('telegramBot.accessTitle', { defaultValue: 'Access & Mini App' })}
                </h3>
                <p className="text-muted-foreground text-xs">
                  {t('telegramBot.accessHint', { defaultValue: 'Who can use the bot · optional Telegram Mini App login' })}
                </p>
              </div>
            </div>

            {enableTelegram ? (
              <div className="grid gap-3 lg:grid-cols-2">
                <FormField
                  control={form.control}
                  name="for_admins_only"
                  render={({ field }) => (
                    <FormItem className="hover:bg-accent/40 flex flex-row items-center justify-between gap-3 rounded-xl border border-border/60 bg-background/40 p-3 transition-colors duration-200">
                      <div className="space-y-0.5">
                        <FormLabel className="flex cursor-pointer items-center gap-2 text-sm font-medium">
                          <Users className="size-4" />
                          {t('settings.telegram.advanced.forAdminsOnly')}
                        </FormLabel>
                        <FormDescription className="text-xs">
                          {t('settings.telegram.advanced.forAdminsOnlyDescription')}
                        </FormDescription>
                        <p className="text-muted-foreground pt-1 text-[11px]">
                          {forAdminsOnly
                            ? t('telegramBot.adminsOnlyOn', { defaultValue: 'Only linked admin Telegram IDs' })
                            : t('telegramBot.adminsOnlyOff', { defaultValue: 'Open to end users / shop' })}
                        </p>
                      </div>
                      <FormControl>
                        <Switch checked={field.value} onCheckedChange={field.onChange} className="cursor-pointer" />
                      </FormControl>
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="mini_app_login"
                  render={({ field }) => (
                    <FormItem className="hover:bg-accent/40 flex flex-row items-center justify-between gap-3 rounded-xl border border-border/60 bg-background/40 p-3 transition-colors duration-200">
                      <div className="space-y-0.5">
                        <FormLabel className="flex cursor-pointer items-center gap-2 text-sm font-medium">
                          <Smartphone className="size-4" />
                          {t('settings.telegram.advanced.miniAppLogin')}
                        </FormLabel>
                        <FormDescription className="text-xs">
                          {t('settings.telegram.advanced.miniAppLoginDescription')}
                        </FormDescription>
                      </div>
                      <FormControl>
                        <Switch checked={field.value} onCheckedChange={field.onChange} className="cursor-pointer" />
                      </FormControl>
                    </FormItem>
                  )}
                />

                {miniAppLogin && (
                  <FormField
                    control={form.control}
                    name="mini_app_url"
                    render={({ field }) => (
                      <FormItem className="space-y-2 lg:col-span-2">
                        <FormLabel className="flex items-center gap-2 text-xs font-medium sm:text-sm">
                          <Smartphone className="size-3.5" />
                          {t('settings.telegram.advanced.miniAppUrl')}
                        </FormLabel>
                        <FormControl>
                          <Input
                            type="url"
                            placeholder={t('settings.telegram.advanced.miniAppUrlPlaceholder')}
                            {...field}
                            className="font-mono text-xs sm:text-sm"
                            dir="ltr"
                          />
                        </FormControl>
                        <FormDescription className="text-xs">
                          {t('settings.telegram.advanced.miniAppUrlDescription')}
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                )}
              </div>
            ) : (
              <p className="text-muted-foreground rounded-xl border border-dashed border-border/70 px-3 py-8 text-center text-xs">
                {t('telegramBot.enableFirst', { defaultValue: 'Turn the bot on to configure reachability.' })}
              </p>
            )}
          </section>
        </div>

        {/* Sticky actions */}
        <div className="bg-background/90 fixed inset-x-0 bottom-0 z-30 border-t border-border/80 backdrop-blur-md supports-[backdrop-filter]:bg-background/70">
          <div className="mx-auto flex max-w-6xl items-center justify-end gap-2 px-3 py-3 sm:px-5 md:px-6">
            <Button type="button" variant="outline" onClick={handleCancel} disabled={isSaving} className="cursor-pointer">
              {t('cancel', { defaultValue: 'Cancel' })}
            </Button>
            <LoaderButton type="submit" loading={isSaving} className="cursor-pointer">
              {t('save', { defaultValue: 'Save' })}
            </LoaderButton>
          </div>
        </div>
      </form>
    </Form>
  )
}
