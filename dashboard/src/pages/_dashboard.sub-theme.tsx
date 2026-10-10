import { EmptyState } from '@/components/common/empty-state'
import PageHeader from '@/components/layout/page-header'
import PageTransition from '@/components/layout/page-transition'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { FeatureTogglesCard } from '@/features/sub-theme/components/feature-toggles-card'
import { ModeControlCard } from '@/features/sub-theme/components/mode-control-card'
import { SummaryCard } from '@/features/sub-theme/components/summary-card'
import { ThemeCard } from '@/features/sub-theme/components/theme-card'
import { SUB_THEME_IDS, draftFromSubscription, isDraftEqual, mergeSubscriptionDraft, type SubThemeDraft } from '@/features/sub-theme/lib/sub-theme'
import { useAdmin } from '@/hooks/use-admin'
import useDirDetection from '@/hooks/use-dir-detection'
import { getGetGeneralSettingsQueryKey, getGetSettingsQueryKey, useGetSettings, useModifySettings } from '@/service/api'
import { hasPermission } from '@/utils/rbac'
import { useQueryClient } from '@tanstack/react-query'
import { Lock, Paintbrush, RefreshCw } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

const extractErrorMessage = (error: any): string | undefined => {
  const detail = error?.data?.detail ?? error?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (detail && typeof detail === 'object') {
    const messages: string[] = []
    const walk = (value: unknown, prefix = '') => {
      if (typeof value === 'string') messages.push(prefix ? `${prefix}: ${value}` : value)
      else if (Array.isArray(value)) value.forEach((item, index) => walk(item, `${prefix}[${index}]`))
      else if (value && typeof value === 'object') Object.entries(value).forEach(([key, item]) => walk(item, prefix ? `${prefix}.${key}` : key))
    }
    walk(detail)
    if (messages.length) return messages.join(', ')
  }
  return error?.message
}

function SubThemeSkeleton() {
  return (
    <div className="mx-auto w-full max-w-[1400px] space-y-6 px-4 py-5 md:px-6 md:py-7">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, index) => (
          <Skeleton key={index} className="h-72 w-full" />
        ))}
      </div>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
        <Skeleton className="h-80 w-full" />
        <Skeleton className="h-80 w-full" />
      </div>
    </div>
  )
}

export default function SubThemePage() {
  const { t } = useTranslation()
  const dir = useDirDetection()
  const { admin } = useAdmin()
  const queryClient = useQueryClient()
  const canEdit = hasPermission(admin, 'settings', 'read') && hasPermission(admin, 'settings', 'update')

  const { data: settings, isLoading, error, refetch, isFetching } = useGetSettings({ query: { enabled: canEdit } })
  const { mutateAsync: modifySettings, isPending: isSaving } = useModifySettings({
    mutation: {
      onSuccess: updated => {
        toast.success(t('subTheme.saveSuccess'))
        queryClient.setQueryData(getGetSettingsQueryKey(), updated)
        if (updated?.general) queryClient.setQueryData(getGetGeneralSettingsQueryKey(), updated.general)
        queryClient.invalidateQueries({ queryKey: ['/api/settings'] })
      },
      onError: (err: any) => {
        toast.error(t('subTheme.saveFailed'), { description: extractErrorMessage(err) })
      },
    },
  })

  const stored = useMemo(() => draftFromSubscription(settings?.subscription), [settings?.subscription])
  const [draft, setDraft] = useState<SubThemeDraft>(stored)

  // Re-sync whenever the stored settings change (initial load, save, refetch)
  useEffect(() => {
    setDraft(stored)
  }, [stored])

  const dirty = !isDraftEqual(draft, stored)

  const update = <K extends keyof SubThemeDraft>(key: K, value: SubThemeDraft[K]) => setDraft(prev => ({ ...prev, [key]: value }))

  const handleSave = async () => {
    const existing = settings?.subscription
    if (!existing) {
      toast.error(t('subTheme.loadFailed'))
      return
    }
    try {
      // PUT replaces the whole `subscription` object: always send the stored one with only appearance fields changed.
      await modifySettings({ data: { subscription: mergeSubscriptionDraft(existing, draft) } })
    } catch {
      // Error toast is handled in the mutation options
    }
  }

  if (!canEdit) {
    return (
      <PageTransition isContentTransition className="w-full">
        <EmptyState icon={Lock} title={t('subTheme.denied')} description={t('subTheme.deniedHint')} />
      </PageTransition>
    )
  }

  return (
    <div className="flex w-full flex-col items-start">
      <div className="animate-fade-in w-full transform-gpu" style={{ animationDuration: '400ms' }}>
        <PageHeader title="subTheme.title" description="subTheme.subtitle" index="09" sectorLabel={t('subTheme.sector')} />
      </div>

      {isLoading ? (
        <SubThemeSkeleton />
      ) : error || !settings?.subscription ? (
        <div className="mx-auto w-full max-w-[1400px] px-4 py-5 md:px-6 md:py-7">
          <EmptyState
            icon={Paintbrush}
            title={t('subTheme.loadFailed')}
            action={
              <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
                <RefreshCw className="size-4" />
                {t('subTheme.retry')}
              </Button>
            }
          />
        </div>
      ) : (
        <PageTransition isContentTransition className="mx-auto w-full max-w-[1400px] space-y-6 px-4 py-5 md:space-y-8 md:px-6 md:py-7">
          <section className="space-y-3" dir={dir}>
            <div className="flex flex-wrap items-end justify-between gap-2">
              <div className="space-y-0.5">
                <h2 className="font-display text-lg font-bold tracking-tight">{t('subTheme.skins.title')}</h2>
                <p className="text-muted-foreground text-xs">{t('subTheme.skins.description')}</p>
              </div>
            </div>
            <div role="radiogroup" aria-label={t('subTheme.skins.title')} className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {SUB_THEME_IDS.map(theme => (
                <ThemeCard
                  key={theme}
                  theme={theme}
                  mode={draft.sub_theme_mode}
                  selected={draft.sub_theme === theme}
                  live={stored.sub_theme === theme}
                  disabled={isSaving}
                  onSelect={value => update('sub_theme', value)}
                />
              ))}
              <ModeControlCard mode={draft.sub_theme_mode} disabled={isSaving} onChange={value => update('sub_theme_mode', value)} />
            </div>
          </section>

          <section className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_340px]" dir={dir}>
            <FeatureTogglesCard draft={draft} disabled={isSaving} onToggle={(key, value) => update(key, value)} />
            <SummaryCard draft={draft} dirty={dirty} isSaving={isSaving} onSave={handleSave} onReset={() => setDraft(stored)} />
          </section>
        </PageTransition>
      )}
    </div>
  )
}
