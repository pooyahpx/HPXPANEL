import type { Subscription, SubTheme, SubThemeMode } from '@/service/api'

export const SUB_THEME_IDS: readonly SubTheme[] = ['terminal', 'aurora', 'nova', 'atlas', 'pulse'] as const

export const DEFAULT_SUB_THEME: SubTheme = 'terminal'
export const DEFAULT_SUB_THEME_MODE: SubThemeMode = 'dark'

export interface SubThemeDraft {
  sub_theme: SubTheme
  sub_theme_mode: SubThemeMode
  sub_show_install_guide: boolean
  sub_show_apps: boolean
  sub_show_usage_chart: boolean
  sub_allow_mode_toggle: boolean
}

export const isSubTheme = (value: unknown): value is SubTheme => typeof value === 'string' && (SUB_THEME_IDS as readonly string[]).includes(value)

/** Read the draft from stored settings, falling back to safe defaults for installs that predate the feature. */
export const draftFromSubscription = (subscription?: Subscription | null): SubThemeDraft => ({
  sub_theme: isSubTheme(subscription?.sub_theme) ? subscription.sub_theme : DEFAULT_SUB_THEME,
  sub_theme_mode: subscription?.sub_theme_mode === 'light' ? 'light' : DEFAULT_SUB_THEME_MODE,
  sub_show_install_guide: subscription?.sub_show_install_guide ?? true,
  sub_show_apps: subscription?.sub_show_apps ?? true,
  sub_show_usage_chart: subscription?.sub_show_usage_chart ?? true,
  sub_allow_mode_toggle: subscription?.sub_allow_mode_toggle ?? false,
})

export const isDraftEqual = (a: SubThemeDraft, b: SubThemeDraft) => (Object.keys(a) as (keyof SubThemeDraft)[]).every(key => a[key] === b[key])

/**
 * PUT /api/settings replaces the whole `subscription` blob, so the payload must always be the
 * full stored object (rules, applications, headers...) with only the appearance fields changed.
 */
export const mergeSubscriptionDraft = (existing: Subscription, draft: SubThemeDraft): Subscription => ({ ...existing, ...draft })
