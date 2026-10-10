import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Loader2, Lock, RotateCcw, Save } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { modeText, st, themeText } from '../lib/i18n'
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
          <CardTitle className="font-display">{st(t, 'subTheme.summary.title', 'Summary')}</CardTitle>
          <Badge variant={dirty ? 'yellow' : 'green'} className="shadow-none normal-case">
            {dirty ? st(t, 'subTheme.summary.unsaved', 'Unsaved') : st(t, 'subTheme.summary.saved', 'Saved')}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <dl className="divide-border divide-y text-sm">
          <div className="flex items-center justify-between gap-3 py-2 first:pt-0">
            <dt className="text-muted-foreground">{st(t, 'subTheme.summary.theme', 'Skin')}</dt>
            <dd className="font-semibold">{themeText(t, draft.sub_theme, 'name')}</dd>
          </div>
          <div className="flex items-center justify-between gap-3 py-2">
            <dt className="text-muted-foreground">{st(t, 'subTheme.summary.mode', 'Default mode')}</dt>
            <dd className="font-semibold">{modeText(t, draft.sub_theme_mode)}</dd>
          </div>
          <div className="flex items-center justify-between gap-3 py-2 last:pb-0">
            <dt className="text-muted-foreground">{st(t, 'subTheme.summary.features', 'Features on')}</dt>
            <dd className="font-semibold">{st(t, 'subTheme.summary.featuresCount', '{{enabled}} of {{total}}', { enabled: enabledFeatures, total: 4 })}</dd>
          </div>
        </dl>

        <div className="border-primary/40 bg-primary/5 text-muted-foreground flex items-start gap-2 border p-3 text-xs leading-relaxed">
          <Lock className="text-primary mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
          <span>{st(t, 'subTheme.summary.lockNote', 'Admin only. Visitors of the subscription page cannot change the theme; the skin is rendered by the server.')}</span>
        </div>

        <div className="flex flex-col gap-2 sm:flex-row lg:flex-col xl:flex-row">
          <Button type="button" className="flex-1" onClick={onSave} disabled={!dirty || isSaving}>
            {isSaving ? <Loader2 className="size-4 animate-spin" /> : <Save className="size-4" />}
            {isSaving ? st(t, 'subTheme.summary.saving', 'Saving...') : st(t, 'subTheme.summary.save', 'Save theme')}
          </Button>
          <Button type="button" variant="outline" onClick={onReset} disabled={!dirty || isSaving}>
            <RotateCcw className="size-4" />
            {st(t, 'subTheme.summary.reset', 'Reset')}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
