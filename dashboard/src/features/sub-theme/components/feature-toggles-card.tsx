import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { BookOpen, LayoutGrid, LineChart, SunMoon, type LucideIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { st } from '../lib/i18n'
import type { SubThemeDraft } from '../lib/sub-theme'

type ToggleKey = 'sub_show_install_guide' | 'sub_show_apps' | 'sub_show_usage_chart' | 'sub_allow_mode_toggle'

const TOGGLES: { key: ToggleKey; i18n: string; icon: LucideIcon; label: string; hint: string }[] = [
  { key: 'sub_show_install_guide', i18n: 'installGuide', icon: BookOpen, label: 'Install guide', hint: 'Three-step quick start: download an app, add the subscription, connect.' },
  { key: 'sub_show_apps', i18n: 'apps', icon: LayoutGrid, label: 'Recommended apps', hint: "App cards with download and import buttons; the card for the visitor's platform is highlighted." },
  { key: 'sub_show_usage_chart', i18n: 'usageChart', icon: LineChart, label: 'Usage chart', hint: 'Traffic usage statistics with time range selector.' },
  { key: 'sub_allow_mode_toggle', i18n: 'modeToggle', icon: SunMoon, label: 'Allow light/dark toggle', hint: 'Let users flip between light and dark. They can never change the skin.' },
]

interface FeatureTogglesCardProps {
  draft: SubThemeDraft
  disabled?: boolean
  onToggle: (key: ToggleKey, value: boolean) => void
}

export function FeatureTogglesCard({ draft, disabled, onToggle }: FeatureTogglesCardProps) {
  const { t } = useTranslation()

  return (
    <Card>
      <CardHeader>
        <CardTitle className="font-display">{st(t, 'subTheme.features.title', 'Page features')}</CardTitle>
        <CardDescription>{st(t, 'subTheme.features.description', 'Show or hide sections on the public subscription page.')}</CardDescription>
      </CardHeader>
      <CardContent className="divide-border divide-y">
        {TOGGLES.map(({ key, i18n, icon: Icon, label, hint }) => (
          <div key={key} className="flex items-center justify-between gap-4 py-3.5 first:pt-0 last:pb-0">
            <div className="flex min-w-0 items-start gap-3">
              <span className="bg-muted/50 text-primary mt-0.5 grid size-9 shrink-0 place-items-center border">
                <Icon className="size-4" aria-hidden="true" />
              </span>
              <div className="min-w-0 space-y-0.5">
                <Label htmlFor={`sub-theme-${key}`} className="cursor-pointer text-sm font-semibold">
                  {st(t, `subTheme.features.${i18n}.label`, label)}
                </Label>
                <p className="text-muted-foreground text-xs leading-relaxed">{st(t, `subTheme.features.${i18n}.hint`, hint)}</p>
              </div>
            </div>
            <Switch id={`sub-theme-${key}`} checked={draft[key]} disabled={disabled} onCheckedChange={value => onToggle(key, value)} />
          </div>
        ))}
      </CardContent>
    </Card>
  )
}
