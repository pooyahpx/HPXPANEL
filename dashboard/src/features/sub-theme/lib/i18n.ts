import type { TFunction } from 'i18next'

/**
 * Translate a Sub Theme key with a mandatory English fallback, so a locale that is missing the
 * `subTheme` namespace never renders a bare key such as `subTheme.summary.title`.
 */
export const st = (t: TFunction, key: string, defaultValue: string, options?: Record<string, unknown>): string => {
  const text = String(t(key, { ...options, defaultValue }))
  // Safety net: if i18n is not ready it returns the raw default, so interpolate `{{vars}}` ourselves.
  return options ? text.replace(/\{\{\s*(\w+)\s*\}\}/g, (match, name: string) => (name in options ? String(options[name]) : match)) : text
}

export const THEME_DEFAULTS: Record<string, { name: string; tag: string; description: string }> = {
  terminal: { name: 'Terminal', tag: 'Pixel', description: 'The classic HPXPANEL look: hard pixel borders, offset shadows and a hacker-console grid.' },
  aurora: { name: 'Aurora', tag: 'Editorial', description: 'Elegant serif headlines with teal and gold accents, generous spacing and rounded pills.' },
  nova: { name: 'Nova', tag: 'Glass', description: 'Soft frosted-glass cards over a teal and cyan mesh, with a floating status orb.' },
  atlas: { name: 'Atlas', tag: 'Ops', description: 'A clean operations dashboard: slate and emerald, crisp cards, subtle grid and dense but tidy data.' },
  pulse: { name: 'Pulse', tag: 'Kinetic', description: 'Electric cyan and lime on near-black with live status pulses and shimmering call-to-actions.' },
}

export const themeText = (t: TFunction, theme: string, field: 'name' | 'tag' | 'description'): string =>
  st(t, `subTheme.themes.${theme}.${field}`, THEME_DEFAULTS[theme]?.[field] ?? theme)

export const modeText = (t: TFunction, mode: string): string => st(t, `subTheme.mode.${mode}`, mode === 'light' ? 'Light' : 'Dark')
