import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Loader2, Lock, RotateCcw, Save } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import type { SubThemeDraft } from '../lib/sub-theme'

interface SummaryCardProps {
  draft: SubThemeDraft
  dirty: boolean
  isSaving: boolean
  onSave: () => void
  onReset: () => void
}

export function SummaryCard({ draft, dirty, isSaving, onSave, onReset }: SummaryCardProps) {
  const { t } = useTranslation()
  const enabledFeatures = [draft.sub_show_install_guide, draft.sub_show_apps, draft.sub_show_usage_chart, draft.sub_allow_mode_toggle].filter(Boolean).length

  return (
    <Card className="lg:sticky lg:top-4">
      <CardHeader className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <CardTitle className="font-display">{t('subTheme.summary.title')}</CardTitle>
          <Badge variant={dirty ? 'yellow' : 'green'} className="shadow-none">
            {dirty ? t('subTheme.summary.unsaved') : t('subTheme.summary.saved')}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <dl className="divide-border divide-y text-sm">
          <div className="flex items-center justify-between gap-3 py-2 first:pt-0">
            <dt className="text-muted-foreground">{t('subTheme.summary.theme')}</dt>
            <dd className="font-semibold">{t(`subTheme.themes.${draft.sub_theme}.name`)}</dd>
          </div>
          <div className="flex items-center justify-between gap-3 py-2">
            <dt className="text-muted-foreground">{t('subTheme.summary.mode')}</dt>
            <dd className="font-semibold">{t(`subTheme.mode.${draft.sub_theme_mode}`)}</dd>
          </div>
          <div className="flex items-center justify-between gap-3 py-2 last:pb-0">
            <dt className="text-muted-foreground">{t('subTheme.summary.features')}</dt>
            <dd className="font-semibold">{t('subTheme.summary.featuresCount', { enabled: enabledFeatures, total: 4 })}</dd>
          </div>
        </dl>

        <div className="border-primary/40 bg-primary/5 text-muted-foreground flex items-start gap-2 border p-3 text-xs leading-relaxed">
          <Lock className="text-primary mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
          <span>{t('subTheme.summary.lockNote')}</span>
        </div>

        <div className="flex flex-col gap-2 sm:flex-row lg:flex-col xl:flex-row">
          <Button type="button" className="flex-1" onClick={onSave} disabled={!dirty || isSaving}>
            {isSaving ? <Loader2 className="size-4 animate-spin" /> : <Save className="size-4" />}
            {isSaving ? t('subTheme.summary.saving') : t('subTheme.summary.save')}
          </Button>
          <Button type="button" variant="outline" onClick={onReset} disabled={!dirty || isSaving}>
            <RotateCcw className="size-4" />
            {t('subTheme.summary.reset')}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
