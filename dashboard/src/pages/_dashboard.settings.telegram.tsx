import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useTranslation } from 'react-i18next'
import { useEffect } from 'react'
import { SubscriptionFormActions } from '@/features/subscriptions/components/subscription-form-actions'
import { Button } from '@/components/ui/button'
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { PasswordInput } from '@/components/ui/password-input'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import { Bot, Globe, Smartphone, Send, Users, RefreshCcw } from 'lucide-react'
import { useSettingsContext } from './_dashboard.settings'
import { toast } from 'sonner'
import { useGetWorkersHealth } from '@/service/api'

const telegramSettingsSchema = z.object({
  enable: z.boolean().default(false),
  token: z.string().optional(),
  proxy_url: z.string().url('Please enter a valid URL').optional().or(z.literal('')),
  mini_app_login: z.boolean().default(false),
  mini_app_url: z.string().url('Please enter a valid URL').optional().or(z.literal('')),
  panel_url: z.string().url('Please enter a valid URL').optional().or(z.literal('')),
  for_admins_only: z.boolean().default(true),
})

type TelegramSettingsFormInput = z.input<typeof telegramSettingsSchema>

const getCurrentPanelUrl = () => {
  const protocol = window.location.protocol
  const host = window.location.host
  return `${protocol}//${host}`
}

function mapTelegramFormToPayload(data: TelegramSettingsFormInput) {
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

export default function TelegramSettings() {
  const { t } = useTranslation()
  const { settings, isLoading, error, updateSettings, isSaving } = useSettingsContext()
  const { data: workersHealth } = useGetWorkersHealth({
    query: {
      retry: false,
      refetchInterval: 30000,
      staleTime: 30000,
    },
  })

  const form = useForm<TelegramSettingsFormInput>({
    resolver: zodResolver(telegramSettingsSchema),
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
  const schedulerStatus = workersHealth?.scheduler?.status?.toLowerCase().trim()
  const nodeStatus = workersHealth?.node?.status?.toLowerCase().trim()
  const isMultiWorkerMode = !!workersHealth && !(schedulerStatus === 'disabled' && nodeStatus === 'disabled')

  useEffect(() => {
    if (settings?.telegram) {
      const telegramData = settings.telegram
      form.reset({
        enable: telegramData.enable || false,
        token: telegramData.token || '',
        proxy_url: telegramData.proxy_url || '',
        mini_app_login: telegramData.mini_app_login || false,
        mini_app_url: telegramData.mini_app_web_url || '',
        panel_url: telegramData.panel_url || '',
        for_admins_only: telegramData.for_admins_only !== undefined ? telegramData.for_admins_only : true,
      })
    }
  }, [settings, form])

  const onSubmit = async (data: TelegramSettingsFormInput) => {
    try {
      await updateSettings(mapTelegramFormToPayload(data))
    } catch {
      // Error handling is done in the parent context
    }
  }

  const handleCancel = () => {
    if (settings?.telegram) {
      const telegramData = settings.telegram
      form.reset({
        enable: telegramData.enable || false,
        token: telegramData.token || '',
        proxy_url: telegramData.proxy_url || '',
        mini_app_login: telegramData.mini_app_login || false,
        mini_app_url: telegramData.mini_app_web_url || '',
        panel_url: telegramData.panel_url || '',
        for_admins_only: telegramData.for_admins_only !== undefined ? telegramData.for_admins_only : true,
      })
      toast.success(t('settings.telegram.cancelSuccess'))
    }
  }

  if (isLoading) {
    return (
      <div className="w-full p-4 sm:py-6 lg:py-8">
        <div className="space-y-6 sm:space-y-8 lg:space-y-10">
          <div className="space-y-4">
            <div className="space-y-2">
              <Skeleton className="h-6 w-48" />
              <Skeleton className="h-4 w-96" />
            </div>
            <Skeleton className="h-16" />
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="space-y-2">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-10" />
                  <Skeleton className="h-3 w-64" />
                </div>
              ))}
            </div>
            <Skeleton className="h-16" />
          </div>

          <div className="flex flex-col gap-3 pt-4 sm:flex-row sm:gap-4">
            <div className="flex-1"></div>
            <div className="flex flex-col gap-3 sm:shrink-0 sm:flex-row sm:gap-4">
              <Skeleton className="h-10 w-24" />
              <Skeleton className="h-10 w-20" />
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex min-h-[400px] items-center justify-center p-4 sm:py-6 lg:py-8">
        <div className="space-y-3 text-center">
          <div className="text-lg text-red-500">⚠️</div>
          <p className="text-sm text-red-500">Error loading settings</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-[calc(100vh-200px)] w-full flex-col">
      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-1 flex-col p-4 sm:py-6 lg:py-8">
          <div className="flex-1 space-y-6 sm:space-y-8 lg:space-y-10">
            <div className="space-y-3">
              <div className="space-y-2">
                <h3 className="text-base font-semibold sm:text-lg">{t('settings.telegram.general.title')}</h3>
                <p className="text-muted-foreground text-xs sm:text-sm">{t('settings.telegram.general.description')}</p>
              </div>

              <FormField
                control={form.control}
                name="enable"
                render={({ field }) => (
                  <FormItem className="bg-card hover:bg-accent/50 flex flex-row items-center justify-between space-y-0 gap-x-3 rounded-lg border p-3 transition-colors sm:p-4">
                    <div className="space-y-0.5">
                      <FormLabel className="flex cursor-pointer items-center gap-2 text-xs font-medium sm:text-sm">
                        <Send className="h-4 w-4" />
                        {t('settings.telegram.general.enable')}
                      </FormLabel>
                      <FormDescription className="text-muted-foreground text-xs sm:text-sm">{t('settings.telegram.general.enableDescription')}</FormDescription>
                    </div>
                    <FormControl>
                      <Switch checked={field.value} onCheckedChange={field.onChange} />
                    </FormControl>
                  </FormItem>
                )}
              />

              {enableTelegram && isMultiWorkerMode && (
                <div className="rounded-lg border border-amber-500/40 bg-amber-500/10 p-3 text-xs text-amber-700 sm:text-sm dark:text-amber-300">
                  {t('settings.telegram.general.longPollingDisabledInMultiWorker', {
                    defaultValue: 'Long polling is disabled in multi-worker mode. Disable NATS and set UVICORN_WORKERS=1.',
                  })}
                </div>
              )}

              {enableTelegram && (
                <div className="grid grid-cols-1 gap-3 sm:gap-4 lg:grid-cols-2">
                  <FormField
                    control={form.control}
                    name="token"
                    render={({ field }) => (
                      <FormItem className="space-y-2">
                        <FormLabel className="flex items-center gap-2 text-xs font-medium sm:text-sm">
                          <Bot className="h-4 w-4" />
                          {t('settings.telegram.general.token')}
                        </FormLabel>
                        <FormControl>
                          <PasswordInput placeholder={t('settings.telegram.general.tokenPlaceholder')} {...field} className="font-mono text-xs sm:text-sm" />
                        </FormControl>
                        <FormDescription className="text-muted-foreground text-xs sm:text-sm">{t('settings.telegram.general.tokenDescription')}</FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="panel_url"
                    render={({ field }) => (
                      <FormItem className="space-y-2 lg:col-span-2">
                        <FormLabel className="flex items-center gap-2 text-xs font-medium sm:text-sm">
                          <Globe className="h-4 w-4" />
                          {t('settings.telegram.general.panelUrl')}
                        </FormLabel>
                        <div className="relative">
                          <FormControl>
                            <Input type="url" placeholder={t('settings.telegram.general.panelUrlPlaceholder')} {...field} className="pr-10 font-mono text-xs sm:text-sm" />
                          </FormControl>
                          <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            className="hover:bg-accent absolute top-1/2 right-1 h-8 w-8 -translate-y-1/2"
                            onClick={e => {
                              e.preventDefault()
                              field.onChange(getCurrentPanelUrl())
                              toast.success(t('settings.telegram.general.panelUrlApplied'))
                            }}
                          >
                            <RefreshCcw className="h-3 w-3" />
                          </Button>
                        </div>
                        <FormDescription className="text-muted-foreground text-xs sm:text-sm">{t('settings.telegram.general.panelUrlDescription')}</FormDescription>
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
                          <Globe className="h-4 w-4" />
                          {t('settings.telegram.general.proxyUrl')}
                        </FormLabel>
                        <FormControl>
                          <Input type="url" placeholder={t('settings.telegram.general.proxyUrlPlaceholder')} {...field} className="font-mono text-xs sm:text-sm" />
                        </FormControl>
                        <FormDescription className="text-muted-foreground text-xs sm:text-sm">{t('settings.telegram.general.proxyUrlDescription')}</FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
              )}
            </div>

            {enableTelegram && (
              <>
                <Separator className="my-3" />

                <div className="space-y-3">
                  <div className="space-y-2">
                    <h3 className="text-base font-semibold sm:text-lg">{t('settings.telegram.advanced.title')}</h3>
                    <p className="text-muted-foreground text-xs sm:text-sm">{t('settings.telegram.advanced.description')}</p>
                  </div>

                  <FormField
                    control={form.control}
                    name="mini_app_login"
                    render={({ field }) => (
                      <FormItem className="bg-card hover:bg-accent/50 flex flex-row items-center justify-between space-y-0 rounded-lg border p-3 transition-colors sm:p-4">
                        <div className="space-y-0.5">
                          <FormLabel className="flex cursor-pointer items-center gap-2 text-xs font-medium sm:text-sm">
                            <Smartphone className="h-4 w-4" />
                            {t('settings.telegram.advanced.miniAppLogin')}
                          </FormLabel>
                          <FormDescription className="text-muted-foreground text-xs sm:text-sm">{t('settings.telegram.advanced.miniAppLoginDescription')}</FormDescription>
                        </div>
                        <FormControl>
                          <Switch checked={field.value} onCheckedChange={field.onChange} />
                        </FormControl>
                      </FormItem>
                    )}
                  />
                  {form.watch('mini_app_login') && (
                    <FormField
                      control={form.control}
                      name="mini_app_url"
                      render={({ field }) => (
                        <FormItem className="space-y-2">
                          <FormLabel className="flex items-center gap-2 text-xs font-medium sm:text-sm">
                            <Smartphone className="h-4 w-4" />
                            {t('settings.telegram.advanced.miniAppUrl')}
                          </FormLabel>
                          <FormControl>
                            <Input type="url" placeholder={t('settings.telegram.advanced.miniAppUrlPlaceholder')} {...field} className="font-mono text-xs sm:text-sm" />
                          </FormControl>
                          <FormDescription className="text-muted-foreground text-xs sm:text-sm">{t('settings.telegram.advanced.miniAppUrlDescription')}</FormDescription>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  )}

                  <FormField
                    control={form.control}
                    name="for_admins_only"
                    render={({ field }) => (
                      <FormItem className="bg-card hover:bg-accent/50 flex flex-row items-center justify-between space-y-0 rounded-lg border p-3 transition-colors sm:p-4">
                        <div className="space-y-0.5">
                          <FormLabel className="flex cursor-pointer items-center gap-2 text-xs font-medium sm:text-sm">
                            <Users className="h-4 w-4" />
                            {t('settings.telegram.advanced.forAdminsOnly')}
                          </FormLabel>
                          <FormDescription className="text-muted-foreground text-xs sm:text-sm">{t('settings.telegram.advanced.forAdminsOnlyDescription')}</FormDescription>
                        </div>
                        <FormControl>
                          <Switch checked={field.value} onCheckedChange={field.onChange} />
                        </FormControl>
                      </FormItem>
                    )}
                  />
                </div>
              </>
            )}
          </div>

          <SubscriptionFormActions onCancel={handleCancel} isSaving={isSaving} />
        </form>
      </Form>
    </div>
  )
}
