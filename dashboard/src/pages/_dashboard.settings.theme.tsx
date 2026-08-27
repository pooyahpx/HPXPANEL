import { useTranslation } from 'react-i18next'
import { useTheme, colorThemes, type ColorTheme, type Radius } from '@/app/providers/theme-provider'
import { useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'
import {
  SunMoon,
  Palette,
  Ruler,
  Eye,
  RotateCcw,
  Sun,
  Moon,
  Monitor,
  CalendarClock,
  BarChart3,
  TrendingUp,
  FileJson2,
  Type,
  Rows3,
  Sparkles,
  Accessibility,
  Check,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import useDirDetection from '@/hooks/use-dir-detection'
import {
  getCoresListUseConfigModal,
  getDatePickerPreference,
  getChartViewTypePreference,
  getUiDensity,
  getFontScale,
  getReducedMotion,
  getMeshBackground,
  setCoresListUseConfigModal,
  setDatePickerPreference,
  setChartViewTypePreference,
  setUiDensity,
  setFontScale,
  setReducedMotion,
  setMeshBackground,
  resetUiAppearancePrefs,
  type DatePickerPreference,
  type ChartViewType,
  type UiDensity,
  type FontScale,
} from '@/utils/userPreferenceStorage'

const colorThemeData = [
  { name: 'default', label: 'theme.default', dot: '#2563eb' },
  { name: 'red', label: 'theme.red', dot: '#ef4444' },
  { name: 'rose', label: 'theme.rose', dot: '#e11d48' },
  { name: 'orange', label: 'theme.orange', dot: '#f97316' },
  { name: 'green', label: 'theme.green', dot: '#22c55e' },
  { name: 'blue', label: 'theme.blue', dot: '#3b82f6' },
  { name: 'yellow', label: 'theme.yellow', dot: '#eab308' },
  { name: 'violet', label: 'theme.violet', dot: '#8b5cf6' },
] as const

const radiusOptions = [
  { value: '0', label: 'theme.radiusNone', description: '0' },
  { value: '0.3rem', label: 'theme.radiusSmall', description: 'S' },
  { value: '0.5rem', label: 'theme.radiusMedium', description: 'M' },
  { value: '0.75rem', label: 'theme.radiusLarge', description: 'L' },
  { value: '1rem', label: 'theme.radiusXl', description: 'XL' },
] as const

const modeOptions = [
  { id: 'light' as const, icon: Sun },
  { id: 'dark' as const, icon: Moon },
  { id: 'system' as const, icon: Monitor },
]

const densityOptions: { id: UiDensity; labelKey: string }[] = [
  { id: 'compact', labelKey: 'theme.densityCompact' },
  { id: 'comfortable', labelKey: 'theme.densityComfortable' },
  { id: 'spacious', labelKey: 'theme.densitySpacious' },
]

const fontScaleOptions: { id: FontScale; label: string }[] = [
  { id: 'sm', label: 'S' },
  { id: 'md', label: 'M' },
  { id: 'lg', label: 'L' },
]

function Segmented<T extends string>({
  value,
  options,
  onChange,
  className,
}: {
  value: T
  options: { id: T; label: string; icon?: React.ReactNode }[]
  onChange: (v: T) => void
  className?: string
}) {
  return (
    <div className={cn('bg-muted/50 grid gap-1 rounded-xl border p-1', className)} style={{ gridTemplateColumns: `repeat(${options.length}, minmax(0, 1fr))` }}>
      {options.map(opt => (
        <button
          key={opt.id}
          type="button"
          onClick={() => onChange(opt.id)}
          className={cn(
            'flex items-center justify-center gap-1.5 rounded-lg px-2 py-2 text-xs font-medium transition-all sm:text-sm',
            value === opt.id ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground hover:bg-background/80 hover:text-foreground',
          )}
        >
          {opt.icon}
          {opt.label}
        </button>
      ))}
    </div>
  )
}

function Panel({ title, icon, description, children, action }: { title: string; icon: React.ReactNode; description?: string; children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <section className="border-border/60 bg-card/40 space-y-3 rounded-2xl border p-4 backdrop-blur-sm sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 space-y-1">
          <div className="flex items-center gap-2">
            <span className="text-primary">{icon}</span>
            <h3 className="text-sm font-semibold sm:text-base">{title}</h3>
          </div>
          {description ? <p className="text-muted-foreground text-xs leading-relaxed">{description}</p> : null}
        </div>
        {action}
      </div>
      {children}
    </section>
  )
}

export default function ThemeSettings() {
  const { t, i18n } = useTranslation()
  const { theme, colorTheme, radius, resolvedTheme, setTheme, setColorTheme, setRadius, resetToDefaults, isSystemTheme } = useTheme()
  const dir = useDirDetection()
  const [isResetting, setIsResetting] = useState(false)
  const [datePickerPreference, setDatePickerPreferenceState] = useState<DatePickerPreference>('locale')
  const [chartViewType, setChartViewTypeState] = useState<ChartViewType>('bar')
  const [coresListUseConfigModal, setCoresListUseConfigModalState] = useState(false)
  const [density, setDensityState] = useState<UiDensity>('comfortable')
  const [fontScale, setFontScaleState] = useState<FontScale>('md')
  const [reducedMotion, setReducedMotionState] = useState(false)
  const [meshBg, setMeshBgState] = useState(true)

  const isDatePickerFollowingLocale = datePickerPreference === 'locale'
  const defaultManualDatePreference: Exclude<DatePickerPreference, 'locale'> = i18n.language?.startsWith('fa') ? 'persian' : 'gregorian'

  useEffect(() => {
    setDatePickerPreferenceState(getDatePickerPreference())
    setChartViewTypeState(getChartViewTypePreference())
    setCoresListUseConfigModalState(getCoresListUseConfigModal())
    setDensityState(getUiDensity())
    setFontScaleState(getFontScale())
    setReducedMotionState(getReducedMotion())
    setMeshBgState(getMeshBackground())
  }, [])

  const colorLabel = useMemo(() => t(colorThemeData.find(c => c.name === colorTheme)?.label || 'theme.default'), [colorTheme, t])

  const notify = (description: string) => {
    toast.success(t('success'), { description, duration: 1800 })
  }

  const handleResetToDefaults = async () => {
    setIsResetting(true)
    try {
      resetToDefaults()
      resetUiAppearancePrefs()
      setDatePickerPreference('locale')
      setChartViewTypePreference('bar')
      setCoresListUseConfigModal(false)
      setDatePickerPreferenceState('locale')
      setChartViewTypeState('bar')
      setCoresListUseConfigModalState(false)
      setDensityState('comfortable')
      setFontScaleState('md')
      setReducedMotionState(false)
      setMeshBgState(true)
      notify(t('theme.resetSuccess'))
    } catch {
      toast.error(t('error'), { description: t('theme.resetFailed') })
    } finally {
      setIsResetting(false)
    }
  }

  return (
    <div dir={dir} className="gap-6 px-3 pt-4 pb-16 sm:px-4 sm:pt-6 lg:grid lg:grid-cols-[minmax(0,1fr)_280px] lg:items-start xl:grid-cols-[minmax(0,1fr)_320px]">
      <div className="space-y-4">
        <header className="space-y-1">
          <p className="text-muted-foreground text-[11px] font-medium tracking-[0.18em] uppercase">{t('theme.studioEyebrow', { defaultValue: 'Appearance studio' })}</p>
          <h2 className="text-xl font-semibold tracking-tight sm:text-2xl">{t('theme.title')}</h2>
          <p className="text-muted-foreground max-w-2xl text-sm">{t('theme.studioIntro', { defaultValue: 'Mode, color, density, motion — tuned live. Your panel, your deck.' })}</p>
        </header>

        <Panel
          title={t('theme.mode')}
          icon={<SunMoon className="h-4 w-4" />}
          description={t('theme.modeDescription')}
          action={
            isSystemTheme ? (
              <span className="text-muted-foreground shrink-0 text-[11px]">
                {t('theme.system')}: {resolvedTheme === 'dark' ? t('theme.dark') : t('theme.light')}
              </span>
            ) : null
          }
        >
          <Segmented
            value={theme}
            onChange={v => {
              setTheme(v)
              notify(t('theme.themeChanged'))
            }}
            options={modeOptions.map(m => ({
              id: m.id,
              label: t(`theme.${m.id}`),
              icon: <m.icon className="h-3.5 w-3.5" />,
            }))}
          />
        </Panel>

        <Panel title={t('theme.color')} icon={<Palette className="h-4 w-4" />} description={t('theme.colorDescription')}>
          <div className="grid grid-cols-4 gap-2 sm:grid-cols-8">
            {colorThemeData.map(color => {
              const active = colorTheme === color.name
              return (
                <button
                  key={color.name}
                  type="button"
                  title={t(color.label)}
                  onClick={() => {
                    if (Object.keys(colorThemes).includes(color.name)) {
                      setColorTheme(color.name as ColorTheme)
                      notify(`${t('theme.themeSaved')} — ${t(color.label)}`)
                    }
                  }}
                  className={cn(
                    'relative flex aspect-square items-center justify-center rounded-xl border transition-all',
                    active ? 'border-primary ring-primary/40 scale-[1.03] ring-2' : 'border-border/60 hover:border-primary/50',
                  )}
                  style={{ background: `linear-gradient(145deg, ${color.dot}, color-mix(in srgb, ${color.dot} 55%, black))` }}
                  aria-label={t(color.label)}
                >
                  {active ? <Check className="h-4 w-4 text-white drop-shadow" /> : null}
                </button>
              )
            })}
          </div>
          <p className="text-muted-foreground text-xs">
            {t('theme.currentTheme')}: <span className="text-foreground font-medium">{colorLabel}</span>
          </p>
        </Panel>

        <div className="grid gap-4 sm:grid-cols-2">
          <Panel title={t('theme.radius')} icon={<Ruler className="h-4 w-4" />} description={t('theme.radiusDescription')}>
            <div className="grid grid-cols-5 gap-1.5">
              {radiusOptions.map(option => {
                const active = radius === option.value
                return (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => {
                      setRadius(option.value as Radius)
                      notify(t('theme.radiusSaved'))
                    }}
                    className={cn(
                      'flex flex-col items-center gap-1.5 rounded-xl border px-1 py-2 text-[10px] transition-colors',
                      active ? 'border-primary bg-primary/10 text-foreground' : 'border-border/60 text-muted-foreground hover:border-primary/40',
                    )}
                  >
                    <span className="bg-muted border-border flex h-8 w-8 items-center justify-center border" style={{ borderRadius: option.value }}>
                      <span className="bg-primary/40 h-3 w-3" style={{ borderRadius: option.value }} />
                    </span>
                    {t(option.label)}
                  </button>
                )
              })}
            </div>
          </Panel>

          <Panel title={t('theme.density', { defaultValue: 'Density' })} icon={<Rows3 className="h-4 w-4" />} description={t('theme.densityDescription', { defaultValue: 'How tight the deck feels.' })}>
            <Segmented
              value={density}
              onChange={v => {
                setDensityState(v)
                setUiDensity(v)
                notify(t('theme.densitySaved', { defaultValue: 'Density updated' }))
              }}
              options={densityOptions.map(d => ({ id: d.id, label: t(d.labelKey, { defaultValue: d.id }) }))}
            />
          </Panel>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Panel title={t('theme.fontScale', { defaultValue: 'Type scale' })} icon={<Type className="h-4 w-4" />} description={t('theme.fontScaleDescription', { defaultValue: 'Base text size for the whole panel.' })}>
            <Segmented
              value={fontScale}
              onChange={v => {
                setFontScaleState(v)
                setFontScale(v)
                notify(t('theme.fontScaleSaved', { defaultValue: 'Type scale updated' }))
              }}
              options={fontScaleOptions.map(f => ({ id: f.id, label: f.label }))}
            />
          </Panel>

          <Panel title={t('theme.chartViewType')} icon={<BarChart3 className="h-4 w-4" />} description={t('theme.chartViewDescription')}>
            <Segmented
              value={chartViewType}
              onChange={v => {
                setChartViewTypeState(v)
                setChartViewTypePreference(v)
                notify(t('theme.chartViewSaved'))
              }}
              options={[
                { id: 'bar' as const, label: t('theme.chartViewBar'), icon: <BarChart3 className="h-3.5 w-3.5" /> },
                { id: 'area' as const, label: t('theme.chartViewArea'), icon: <TrendingUp className="h-3.5 w-3.5" /> },
              ]}
            />
          </Panel>
        </div>

        <Panel title={t('theme.datePicker')} icon={<CalendarClock className="h-4 w-4" />} description={t('theme.datePickerDescription')}>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center justify-between gap-3 sm:justify-start">
              <span className="text-xs font-medium">{t('theme.datePickerFollowLocale')}</span>
              <Switch
                checked={isDatePickerFollowingLocale}
                onCheckedChange={checked => {
                  const next = checked ? 'locale' : defaultManualDatePreference
                  setDatePickerPreferenceState(next)
                  setDatePickerPreference(next)
                  notify(t('theme.datePickerPreferenceSaved'))
                }}
              />
            </div>
            <div className="flex gap-2">
              {(['gregorian', 'persian'] as const).map(option => (
                <Button
                  key={option}
                  type="button"
                  size="sm"
                  variant={datePickerPreference === option ? 'default' : 'outline'}
                  disabled={isDatePickerFollowingLocale}
                  onClick={() => {
                    setDatePickerPreferenceState(option)
                    setDatePickerPreference(option)
                    notify(t('theme.datePickerPreferenceSaved'))
                  }}
                >
                  {option === 'gregorian' ? t('theme.datePickerModeGregorian') : t('theme.datePickerModePersian')}
                </Button>
              ))}
            </div>
          </div>
        </Panel>

        <div className="grid gap-4 sm:grid-cols-2">
          <Panel title={t('theme.atmosphere', { defaultValue: 'Atmosphere' })} icon={<Sparkles className="h-4 w-4" />} description={t('theme.atmosphereDescription', { defaultValue: 'Mesh glow behind the deck.' })}>
            <div className="flex items-center justify-between gap-3">
              <span className="text-xs font-medium">{t('theme.meshBackground', { defaultValue: 'Background mesh' })}</span>
              <Switch
                checked={meshBg}
                onCheckedChange={checked => {
                  setMeshBgState(checked)
                  setMeshBackground(checked)
                  notify(t('theme.meshSaved', { defaultValue: 'Atmosphere updated' }))
                }}
              />
            </div>
          </Panel>

          <Panel title={t('theme.accessibility', { defaultValue: 'Motion' })} icon={<Accessibility className="h-4 w-4" />} description={t('theme.reducedMotionDescription', { defaultValue: 'Cut animations for focus and comfort.' })}>
            <div className="flex items-center justify-between gap-3">
              <span className="text-xs font-medium">{t('theme.reducedMotion', { defaultValue: 'Reduced motion' })}</span>
              <Switch
                checked={reducedMotion}
                onCheckedChange={checked => {
                  setReducedMotionState(checked)
                  setReducedMotion(checked)
                  notify(t('theme.motionSaved', { defaultValue: 'Motion preference saved' }))
                }}
              />
            </div>
          </Panel>
        </div>

        <Panel title={t('theme.coresListEditor')} icon={<FileJson2 className="h-4 w-4" />} description={t('theme.coresListEditorDescription')}>
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <p className="text-xs font-medium">{t('theme.coresListEditorModal')}</p>
              <p className="text-muted-foreground text-[11px]">{t('theme.coresListEditorModalHint')}</p>
            </div>
            <Switch
              checked={coresListUseConfigModal}
              onCheckedChange={checked => {
                setCoresListUseConfigModalState(checked)
                setCoresListUseConfigModal(checked)
                notify(t('theme.coresListEditorSaved'))
              }}
            />
          </div>
        </Panel>

        <section className="border-border/60 flex flex-col gap-3 rounded-2xl border border-dashed p-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <RotateCcw className="text-primary h-4 w-4" />
              <p className="text-sm font-semibold">{t('theme.resetToDefaults')}</p>
            </div>
            <p className="text-muted-foreground text-xs">{t('theme.resetDescription')}</p>
          </div>
          <Button variant="outline" onClick={handleResetToDefaults} disabled={isResetting} className="w-full sm:w-auto">
            {isResetting ? t('theme.resetting') : t('theme.reset')}
          </Button>
        </section>
      </div>

      <aside className="lg:sticky lg:top-20">
        <div className="border-border/60 from-card/80 to-muted/20 space-y-4 rounded-2xl border bg-gradient-to-b p-4 shadow-sm backdrop-blur-md">
          <div className="flex items-center gap-2">
            <Eye className="text-primary h-4 w-4" />
            <p className="text-sm font-semibold">{t('theme.preview')}</p>
          </div>
          <p className="text-muted-foreground text-xs">{t('theme.previewDescription')}</p>

          <div className="border-border/70 bg-background space-y-3 border p-3" style={{ borderRadius: radius }}>
            <div className="flex items-center justify-between gap-2">
              <div>
                <p className="text-xs font-semibold">{t('theme.dashboardPreview')}</p>
                <p className="text-muted-foreground text-[10px]">
                  {colorLabel} · {resolvedTheme === 'dark' ? t('theme.dark') : t('theme.light')} · {density}
                </p>
              </div>
              <div className="flex gap-1">
                <span className="bg-primary h-2 w-2 rounded-full" />
                <span className="bg-chart-2 h-2 w-2 rounded-full" />
                <span className="bg-chart-3 h-2 w-2 rounded-full" />
              </div>
            </div>
            <div className="bg-primary/15 h-16 w-full overflow-hidden border" style={{ borderRadius: radius }}>
              <div className="bg-primary/40 h-full w-2/3" style={{ borderRadius: radius }} />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-muted text-muted-foreground flex h-8 items-center rounded border px-2 text-[10px]" style={{ borderRadius: radius }}>
                {t('theme.sampleInput')}
              </div>
              <div className="bg-primary text-primary-foreground flex h-8 items-center justify-center text-[10px] font-semibold" style={{ borderRadius: radius }}>
                {t('theme.primaryButton')}
              </div>
            </div>
            <div className="text-muted-foreground grid grid-cols-2 gap-2 text-[10px]">
              <div className="bg-muted/50 rounded border px-2 py-1.5" style={{ borderRadius: radius }}>
                {t('theme.fontScale', { defaultValue: 'Type' })}: {fontScale.toUpperCase()}
              </div>
              <div className="bg-muted/50 rounded border px-2 py-1.5" style={{ borderRadius: radius }}>
                {t('theme.meshBackground', { defaultValue: 'Mesh' })}: {meshBg ? 'ON' : 'OFF'}
              </div>
            </div>
          </div>
        </div>
      </aside>
    </div>
  )
}
