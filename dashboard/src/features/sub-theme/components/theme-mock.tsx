import { cn } from '@/lib/utils'
import type { SubTheme, SubThemeMode } from '@/service/api'
import type { CSSProperties } from 'react'

interface Palette {
  bg: string
  card: string
  fg: string
  muted: string
  primary: string
  accent: string
  border: string
  ok: string
  onPrimary: string
}

interface SkinSpec {
  dark: Palette
  light: Palette
  radius: number
  btnRadius: number
  borderWidth: number
  fontFamily: string
  titleStyle: CSSProperties
  background?: (p: Palette) => string | undefined
  card?: (p: Palette) => CSSProperties
  button?: (p: Palette) => CSSProperties
}

const SKINS: Record<SubTheme, SkinSpec> = {
  terminal: {
    dark: { bg: '#0b1020', card: '#0f1629', fg: '#e8eef7', muted: '#1b2438', primary: '#5b8dee', accent: '#5b8dee', border: '#7d8ba6', ok: '#2dbf7d', onPrimary: '#0b1020' },
    light: { bg: '#f4f6fa', card: '#ffffff', fg: '#111a2e', muted: '#e3e8f0', primary: '#3355d6', accent: '#3355d6', border: '#25304a', ok: '#1f9a62', onPrimary: '#ffffff' },
    radius: 0,
    btnRadius: 0,
    borderWidth: 2,
    fontFamily: '"JetBrains Mono", ui-monospace, monospace',
    titleStyle: { textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 700 },
    background: p => `linear-gradient(${p.primary}14 1px, transparent 1px), linear-gradient(90deg, ${p.primary}14 1px, transparent 1px)`,
    card: p => ({ boxShadow: `4px 4px 0 ${p.border}` }),
    button: p => ({ boxShadow: `2px 2px 0 ${p.border}` }),
  },
  aurora: {
    dark: { bg: '#0a1215', card: '#0d181c', fg: '#e9f6f3', muted: '#142228', primary: '#22bfae', accent: '#d6b86a', border: '#d6b86a55', ok: '#3fcf9a', onPrimary: '#06161a' },
    light: { bg: '#effcf9', card: '#ffffff', fg: '#0c1f23', muted: '#dcf1ed', primary: '#0b8a7c', accent: '#a8802f', border: '#a8802f66', ok: '#12875c', onPrimary: '#ffffff' },
    radius: 16,
    btnRadius: 999,
    borderWidth: 1,
    fontFamily: '"DM Sans", system-ui, sans-serif',
    titleStyle: { fontFamily: '"Playfair Display", Georgia, serif', fontStyle: 'italic', fontWeight: 500, fontSize: 15 },
    background: p => `radial-gradient(120% 80% at 10% -10%, ${p.primary}33, transparent 60%), radial-gradient(90% 70% at 100% 100%, ${p.accent}22, transparent 60%)`,
    card: p => ({ boxShadow: `0 18px 30px -22px ${p.primary}88` }),
  },
  nova: {
    dark: { bg: '#0a1b25', card: '#ffffff12', fg: '#eafbfb', muted: '#ffffff1c', primary: '#2be0c8', accent: '#37c9f2', border: '#ffffff30', ok: '#4ff0b0', onPrimary: '#05202a' },
    light: { bg: '#e4f4f7', card: '#ffffff99', fg: '#0c2230', muted: '#ffffffaa', primary: '#0a7d78', accent: '#0b88ad', border: '#ffffffd0', ok: '#0f8f63', onPrimary: '#ffffff' },
    radius: 20,
    btnRadius: 999,
    borderWidth: 1,
    fontFamily: '"Manrope", system-ui, sans-serif',
    titleStyle: { fontFamily: '"Syne", system-ui, sans-serif', fontWeight: 800, fontSize: 15, letterSpacing: '-0.02em' },
    background: p =>
      `radial-gradient(70% 80% at 0% 0%, ${p.primary}66, transparent 60%), radial-gradient(70% 80% at 100% 10%, ${p.accent}55, transparent 60%), radial-gradient(90% 70% at 50% 110%, #5a6f8a77, transparent 60%)`,
    card: () => ({ backdropFilter: 'blur(10px)', boxShadow: '0 10px 28px -14px rgba(0,0,0,.5), inset 0 1px 0 rgba(255,255,255,.18)' }),
    button: p => ({ background: `linear-gradient(120deg, ${p.primary}, ${p.accent})`, border: 'none' }),
  },
  atlas: {
    dark: { bg: '#0e131a', card: '#131a22', fg: '#eef2f7', muted: '#1c2530', primary: '#10b981', accent: '#10b981', border: '#29333f', ok: '#34d399', onPrimary: '#04140e' },
    light: { bg: '#f3f6fa', card: '#ffffff', fg: '#111a2a', muted: '#e8edf4', primary: '#047857', accent: '#047857', border: '#d3dce8', ok: '#047857', onPrimary: '#ffffff' },
    radius: 10,
    btnRadius: 8,
    borderWidth: 1,
    fontFamily: '"Source Sans 3", system-ui, sans-serif',
    titleStyle: { fontFamily: '"Outfit", system-ui, sans-serif', fontWeight: 600, fontSize: 14, letterSpacing: '-0.01em' },
    background: p => `linear-gradient(${p.fg}09 1px, transparent 1px), linear-gradient(90deg, ${p.fg}09 1px, transparent 1px)`,
    card: p => ({ borderLeft: `3px solid ${p.primary}`, boxShadow: '0 1px 2px rgba(0,0,0,.2)' }),
    button: () => ({ border: 'none' }),
  },
  pulse: {
    dark: { bg: '#060b0d', card: '#0a1215', fg: '#e8f8fa', muted: '#122126', primary: '#00e5ff', accent: '#9be83a', border: '#00e5ff44', ok: '#9be83a', onPrimary: '#04141a' },
    light: { bg: '#eaf6f8', card: '#ffffff', fg: '#07181d', muted: '#d6ebee', primary: '#007f99', accent: '#4d8a0e', border: '#007f9955', ok: '#4d8a0e', onPrimary: '#ffffff' },
    radius: 5,
    btnRadius: 4,
    borderWidth: 1,
    fontFamily: '"IBM Plex Sans", system-ui, sans-serif',
    titleStyle: { fontFamily: '"Space Grotesk", system-ui, sans-serif', fontWeight: 700, fontSize: 16, letterSpacing: '-0.03em' },
    background: p => `radial-gradient(80% 70% at 100% -10%, ${p.primary}33, transparent 60%), radial-gradient(70% 60% at 0% 110%, ${p.accent}22, transparent 60%)`,
    card: p => ({ borderLeft: `3px solid ${p.primary}` }),
    button: p => ({ background: `linear-gradient(110deg, ${p.primary}, ${p.accent})`, border: 'none' }),
  },
}

interface ThemeMockProps {
  theme: SubTheme
  mode: SubThemeMode
  className?: string
}

/** CSS-only miniature of the public subscription page for a given skin. */
export function ThemeMock({ theme, mode, className }: ThemeMockProps) {
  const skin = SKINS[theme]
  const p = skin[mode]
  const bw = skin.borderWidth

  const surface: CSSProperties = {
    border: `${bw}px solid ${p.border}`,
    borderRadius: skin.radius,
    background: p.card,
    ...skin.card?.(p),
  }
  const button: CSSProperties = {
    background: p.primary,
    color: p.onPrimary,
    borderRadius: skin.btnRadius,
    border: `${bw}px solid ${p.border}`,
    ...skin.button?.(p),
  }
  const pill = (color: string): CSSProperties => ({ background: `${color}33`, color, borderRadius: skin.btnRadius })

  return (
    <div
      dir="ltr"
      aria-hidden="true"
      className={cn('pointer-events-none relative h-48 w-full overflow-hidden p-3 select-none', className)}
      style={{
        background: p.bg,
        backgroundImage: skin.background?.(p),
        backgroundSize: theme === 'terminal' || theme === 'atlas' ? '14px 14px' : undefined,
        color: p.fg,
        fontFamily: skin.fontFamily,
      }}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <span
            className="block size-3.5"
            style={{
              background: theme === 'pulse' || theme === 'nova' ? `linear-gradient(135deg, ${p.primary}, ${p.accent})` : p.primary,
              borderRadius: theme === 'aurora' ? 2 : theme === 'nova' ? 999 : skin.btnRadius === 999 ? 4 : skin.btnRadius,
              transform: theme === 'aurora' ? 'rotate(45deg)' : undefined,
            }}
          />
          <span className="text-[8px] font-bold tracking-[0.2em]" style={{ opacity: 0.85 }}>
            HPXPANEL
          </span>
        </div>
        <span className="px-2 py-0.5 text-[7px] font-bold tracking-widest uppercase" style={{ ...pill(p.primary), border: theme === 'atlas' ? `1px solid ${p.border}` : undefined }}>
          sub
        </span>
      </div>

      <div className="mt-2.5 truncate leading-none" style={skin.titleStyle}>
        <span style={{ fontSize: skin.titleStyle.fontSize ?? 12 }}>Dashboard</span>
      </div>

      <div className="mt-2.5 flex items-center gap-3 p-2.5" style={surface}>
        <div className="relative grid size-11 shrink-0 place-items-center rounded-full" style={{ background: `conic-gradient(${p.ok} 0 68%, ${p.muted} 0)` }}>
          <div className="grid size-[30px] place-items-center rounded-full text-[8px] font-bold" style={{ background: theme === 'nova' ? p.bg : p.card }}>
            68%
          </div>
        </div>
        <div className="min-w-0 flex-1 space-y-1.5">
          <div className="flex items-center gap-1.5">
            <span className={cn('block size-1.5 rounded-full', theme === 'pulse' && 'animate-pulse')} style={{ background: p.ok }} />
            <span className="text-[8px] font-bold tracking-widest uppercase" style={{ color: p.ok }}>
              Active
            </span>
          </div>
          <div className="h-1.5 w-full overflow-hidden" style={{ background: p.muted, borderRadius: skin.btnRadius === 999 ? 999 : Math.min(skin.btnRadius, 3) }}>
            <div className="h-full w-[68%]" style={{ background: theme === 'pulse' ? `linear-gradient(90deg, ${p.primary}, ${p.accent})` : p.ok, borderRadius: 'inherit' }} />
          </div>
          <div className="flex gap-1">
            <span className="h-1.5 w-8" style={{ background: p.muted, borderRadius: 3 }} />
            <span className="h-1.5 w-5" style={{ background: p.muted, borderRadius: 3 }} />
          </div>
        </div>
      </div>

      <div className="mt-2.5 flex items-center gap-2">
        <span className="px-3 py-1 text-[8px] font-bold tracking-wider uppercase" style={button}>
          Copy URL
        </span>
        <span className="px-2.5 py-1 text-[8px] font-semibold" style={{ border: `${bw}px solid ${p.border}`, borderRadius: skin.btnRadius, background: 'transparent' }}>
          QR
        </span>
        <span className="ms-auto flex gap-1">
          {[0, 1, 2].map(i => (
            <span key={i} className="block h-1.5 w-4" style={{ background: i === 0 ? p.primary : p.muted, borderRadius: skin.btnRadius === 999 ? 999 : 2 }} />
          ))}
        </span>
      </div>
    </div>
  )
}
