import PageHeader from '@/components/layout/page-header'
import { Form } from '@/components/ui/form'
import { MotherConfigUsagePanel } from '@/features/subscriptions/components/mother-config-usage-panel'
import { SubscriptionExternalConfigsSection } from '@/features/subscriptions/components/subscription-external-configs-section'
import { SubscriptionFormActions } from '@/features/subscriptions/components/subscription-form-actions'
import { SubscriptionSettingsSkeleton } from '@/features/subscriptions/components/subscription-settings-skeleton'
import {
  normalizeCustomVariablesForPayload,
  subscriptionSchema,
  type SubscriptionFormData,
} from '@/features/subscriptions/components/subscription-settings-schema'
import { useAdmin } from '@/hooks/use-admin'
import { getGetSettingsQueryKey, useGetSettings, useModifySettings } from '@/service/api'
import { hasPermission } from '@/utils/rbac'
import { zodResolver } from '@hookform/resolvers/zod'
import { useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { FieldErrors, useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { Navigate } from 'react-router'
import { toast } from 'sonner'

export default function MotherConfigsPage() {
  const { t } = useTranslation()
  const { admin } = useAdmin()
  const queryClient = useQueryClient()
  const canManage = hasPermission(admin, 'settings', 'read') && hasPermission(admin, 'settings', 'update')

  const { data: settings, isLoading, error } = useGetSettings({
    query: { enabled: canManage },
  })
  const { mutateAsync: modifySettings, isPending: isSaving } = useModifySettings()

  const form = useForm<SubscriptionFormData>({
    resolver: zodResolver(subscriptionSchema),
    defaultValues: {
      url_prefix: '',
      update_interval: 24,
      support_url: '',
      profile_title: '',
      announce: '',
      announce_url: '',
      allow_browser_config: true,
      disable_sub_template: false,
      randomize_order: false,
      custom_variables: [],
      external_configs: [],
      response_headers: {},
      rules: [],
      applications: [],
      manual_sub_request: {
        links: true,
        links_base64: true,
        xray: true,
        wireguard: true,
        openvpn: true,
        sing_box: true,
        clash: true,
        clash_meta: true,
        outline: true,
      },
    },
  })

  useEffect(() => {
    if (!settings?.subscription) return
    const s = settings.subscription
    form.reset({
      url_prefix: s.url_prefix || '',
      update_interval: s.update_interval || 24,
      support_url: s.support_url || '',
      profile_title: s.profile_title || '',
      announce: s.announce || '',
      announce_url: s.announce_url || '',
      allow_browser_config: s.allow_browser_config ?? true,
      disable_sub_template: s.disable_sub_template ?? false,
      randomize_order: s.randomize_order ?? false,
      custom_variables: s.custom_variables || [],
      external_configs: (s.external_configs || []).map(item => ({
        name: item.name || '',
        link: item.link || '',
        enabled: item.enabled ?? true,
        respect_user_quota: item.respect_user_quota ?? true,
      })),
      response_headers: Object.fromEntries(
        Object.entries(s.response_headers || {}).map(([key, value]) => [
          key,
          typeof value === 'string' ? value : JSON.stringify(value),
        ]),
      ),
      rules:
        s.rules?.map(rule => ({
          pattern: rule.pattern,
          target: rule.target,
          response_headers: Object.fromEntries(
            Object.entries(rule.response_headers || {}).map(([key, value]) => [
              key,
              typeof value === 'string' ? value : JSON.stringify(value),
            ]),
          ),
        })) || [],
      applications: s.applications || [],
      manual_sub_request: {
        links: s.manual_sub_request?.links ?? true,
        links_base64: s.manual_sub_request?.links_base64 ?? true,
        xray: s.manual_sub_request?.xray ?? true,
        wireguard: s.manual_sub_request?.wireguard ?? true,
        openvpn: s.manual_sub_request?.openvpn ?? true,
        sing_box: s.manual_sub_request?.sing_box ?? true,
        clash: s.manual_sub_request?.clash ?? true,
        clash_meta: s.manual_sub_request?.clash_meta ?? true,
        outline: s.manual_sub_request?.outline ?? true,
      },
    })
  }, [settings, form])

  if (!canManage) {
    return <Navigate to="/" replace />
  }

  const onSubmit = async (data: SubscriptionFormData) => {
    try {
      const processedExternalConfigs = (data.external_configs || [])
        .map(item => ({
          name: item.name?.trim() || '',
          link: item.link?.trim() || '',
          enabled: item.enabled ?? true,
          respect_user_quota: item.respect_user_quota ?? true,
        }))
        .filter(item => item.link)

      await modifySettings({
        data: {
          subscription: {
            ...settings?.subscription,
            ...data,
            custom_variables: normalizeCustomVariablesForPayload(data.custom_variables),
            external_configs: processedExternalConfigs,
          },
        },
      })
      await queryClient.invalidateQueries({ queryKey: getGetSettingsQueryKey() })
      toast.success(t('settings.subscriptions.saveSuccess', { defaultValue: 'Settings saved' }))
    } catch (err: any) {
      toast.error(err?.data?.detail || err?.message || t('settings.subscriptions.saveFailed', { defaultValue: 'Failed to save' }))
    }
  }

  const onInvalid = (errors: FieldErrors<SubscriptionFormData>) => {
    const first = errors.external_configs
    const msg =
      (Array.isArray(first) && first.find(Boolean)?.link?.message) ||
      t('validation.formHasErrors', { defaultValue: 'Please fix the form errors before submitting' })
    toast.error(typeof msg === 'string' ? msg : t('validation.formHasErrors', { defaultValue: 'Please fix the form errors before submitting' }))
  }

  return (
    <div className="flex w-full flex-col">
      <PageHeader
        title="settings.motherConfigs.title"
        description="settings.motherConfigs.description"
        index="MC"
        sectorLabel="Subscriptions"
      />
      {isLoading ? (
        <SubscriptionSettingsSkeleton />
      ) : error ? (
        <div className="flex min-h-[320px] items-center justify-center p-4">
          <p className="text-sm text-red-500">Error loading settings</p>
        </div>
      ) : (
        <div className="w-full">
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit, onInvalid)} className="space-y-6 p-4 sm:space-y-8 sm:py-6 lg:py-8">
              <MotherConfigUsagePanel />
              <div className="from-emerald-500/10 via-background to-sky-500/5 relative overflow-hidden rounded-2xl border border-white/5 bg-gradient-to-br p-4 sm:p-6">
                <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgb(var(--mesh-a)/0.35),transparent_55%)]" />
                <div className="relative">
                  <SubscriptionExternalConfigsSection form={form} standalone />
                </div>
              </div>
              <SubscriptionFormActions
                isSaving={isSaving}
                onCancel={() => {
                  if (settings?.subscription) {
                    form.reset()
                    toast.success(t('settings.subscriptions.cancelSuccess', { defaultValue: 'Changes discarded' }))
                  }
                }}
              />
            </form>
          </Form>
        </div>
      )}
    </div>
  )
}
