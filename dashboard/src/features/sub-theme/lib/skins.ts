import type { SubTheme } from '@/service/api'
import type { CSSProperties } from 'react'

export interface Palette {
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

export interface SkinSpec {
  dark: Palette
  light: Palette
  radius: number
  btnRadius: number
  borderWidth: number
  fontFamily: string
  titleStyle: CSSProperties
  background?: (p: Palette) => string | undefined
  backgroundSize?: string
  card?: (p: Palette) => CSSProperties
  button?: (p: Palette) => CSSProperties
}

/** Visual tokens mirroring the server-rendered subscription page skins (app/templates/subscription/index.html). */
export const SKINS: Record<SubTheme, SkinSpec> = {
  terminal: {
    dark: { bg: '#0b1020', card: '#0f1629', fg: '#e8eef7', muted: '#1b2438', primary: '#5b8dee', accent: '#5b8dee', border: '#7d8ba6', ok: '#2dbf7d', onPrimary: '#0b1020' },
    light: { bg: '#f4f6fa', card: '#ffffff', fg: '#111a2e', muted: '#e3e8f0', primary: '#3355d6', accent: '#3355d6', border: '#25304a', ok: '#1f9a62', onPrimary: '#ffffff' },
    radius: 0,
    btnRadius: 0,
    borderWidth: 2,
    fontFamily: '"JetBrains Mono", ui-monospace, monospace',
    titleStyle: { textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 700 },
    background: p => `linear-gradient(${p.primary}18 1px, transparent 1px), linear-gradient(90deg, ${p.primary}18 1px, transparent 1px)`,
    backgroundSize: '12px 12px',
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
    titleStyle: { fontFamily: '"Playfair Display", Georgia, serif', fontStyle: 'italic', fontWeight: 500, fontSize: 24, lineHeight: 1 },
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
    titleStyle: { fontFamily: '"Syne", system-ui, sans-serif', fontWeight: 800, fontSize: 16, letterSpacing: '-0.02em' },
    background: p =>
      `radial-gradient(70% 80% at 0% 0%, ${p.primary}66, transparent 60%), radial-gradient(70% 80% at 100% 10%, ${p.accent}55, transparent 60%), radial-gradient(90% 70% at 50% 110%, #5a6f8a77, transparent 60%)`,
    card: () => ({ backdropFilter: 'blur(10px)', boxShadow: '0 10px 28px -14px rgba(0,0,0,.5), inset 0 1px 0 rgba(255,255,255,.18)' }),
    button: p => ({ background: `linear-gradient(120deg, ${p.primary}, ${p.accent})`, border: 'none' }),
  },
  atlas: {
    dark: { bg: '#0e131a', card: '#131a22', fg: '#eef2f7', muted: '#1c2530', primary: '#10b981', accent: '#10b981', border: '#29333f', ok: '#34d399', onPrimary: '#04140e' },
    light: { bg: '#f3f6fa', card: '#ffffff', fg: '#111a2a', muted: '#e8edf4', primary: '#047857', accent: '#047857', border: '#d3dce8', ok: '#047857', onPrimary: '#ffffff' },
    radius: 8,
    btnRadius: 6,
    borderWidth: 1,
    fontFamily: '"Source Sans 3", system-ui, sans-serif',
    titleStyle: { fontFamily: '"Outfit", system-ui, sans-serif', fontWeight: 600, fontSize: 13, letterSpacing: '-0.01em' },
    background: p => `linear-gradient(${p.fg}09 1px, transparent 1px), linear-gradient(90deg, ${p.fg}09 1px, transparent 1px)`,
    backgroundSize: '14px 14px',
    card: p => ({ borderLeft: `3px solid ${p.primary}`, boxShadow: '0 1px 2px rgba(0,0,0,.2)' }),
    button: () => ({ border: 'none' }),
  },
  pulse: {
    dark: { bg: '#04080a', card: '#080f12', fg: '#e8f8fa', muted: '#101c21', primary: '#00e5ff', accent: '#9be83a', border: '#00e5ff66', ok: '#9be83a', onPrimary: '#04141a' },
    light: { bg: '#eaf6f8', card: '#ffffff', fg: '#07181d', muted: '#d6ebee', primary: '#007f99', accent: '#4d8a0e', border: '#007f9966', ok: '#4d8a0e', onPrimary: '#ffffff' },
    radius: 5,
    btnRadius: 4,
    borderWidth: 1,
    fontFamily: '"IBM Plex Sans", system-ui, sans-serif',
    titleStyle: { fontFamily: '"Space Grotesk", system-ui, sans-serif', fontWeight: 700, fontSize: 20, letterSpacing: '-0.03em', lineHeight: 0.95 },
    background: p => `radial-gradient(80% 70% at 100% -10%, ${p.primary}33, transparent 60%), radial-gradient(70% 60% at 0% 110%, ${p.accent}22, transparent 60%)`,
    card: p => ({ boxShadow: `0 0 18px -8px ${p.primary}aa, inset 0 0 14px -12px ${p.primary}` }),
    button: p => ({ background: `linear-gradient(110deg, ${p.primary}, ${p.accent})`, border: 'none' }),
  },
  ember: {
    dark: { bg: '#131110', card: '#1b1816', fg: '#f4efe9', muted: '#2a2623', primary: '#ffb21f', accent: '#ff7a1a', border: '#3b3530', ok: '#7bd88f', onPrimary: '#1a1104' },
    light: { bg: '#e8e6e3', card: '#ffffff', fg: '#1a1714', muted: '#d9d5d0', primary: '#b45f00', accent: '#c2410c', border: '#c9c3bc', ok: '#15803d', onPrimary: '#ffffff' },
    radius: 4,
    btnRadius: 2,
    borderWidth: 1,
    fontFamily: '"Space Grotesk", system-ui, sans-serif',
    titleStyle: { fontFamily: '"Space Grotesk", system-ui, sans-serif', fontWeight: 700, fontSize: 20, letterSpacing: '-0.02em', textTransform: 'uppercase', lineHeight: 1 },
    background: p => `repeating-linear-gradient(0deg, ${p.primary}0d 0 1px, transparent 1px 16px)`,
    card: p => ({ borderTop: `3px solid ${p.primary}`, boxShadow: '0 1px 0 rgba(255,255,255,.04)' }),
    button: () => ({ border: 'none', textTransform: 'uppercase', letterSpacing: '0.06em' }),
  },
  folio: {
    dark: { bg: '#0a0a0a', card: '#101010', fg: '#f6f6f1', muted: '#1b1b1b', primary: '#c6f432', accent: '#c6f432', border: '#303030', ok: '#c6f432', onPrimary: '#0a0a0a' },
    light: { bg: '#fafaf8', card: '#ffffff', fg: '#0a0a0a', muted: '#ececea', primary: '#3f6212', accent: '#3f6212', border: '#cfcfca', ok: '#3f6212', onPrimary: '#ffffff' },
    radius: 0,
    btnRadius: 0,
    borderWidth: 1,
    fontFamily: '"Outfit", system-ui, sans-serif',
    titleStyle: { fontFamily: '"Outfit", system-ui, sans-serif', fontWeight: 700, fontSize: 26, letterSpacing: '-0.04em', lineHeight: 0.95 },
    card: () => ({ boxShadow: 'none' }),
    button: () => ({ border: 'none', fontWeight: 700 }),
  },
  harbor: {
    dark: { bg: '#0c1722', card: '#122234', fg: '#e8f1f8', muted: '#1b3047', primary: '#38bdf8', accent: '#7dd3fc', border: '#26425e', ok: '#4ade80', onPrimary: '#05222f' },
    light: { bg: '#edf3f8', card: '#ffffff', fg: '#0f2233', muted: '#dce8f2', primary: '#0369a1', accent: '#0284c7', border: '#c2d5e5', ok: '#15803d', onPrimary: '#ffffff' },
    radius: 16,
    btnRadius: 12,
    borderWidth: 1,
    fontFamily: '"Manrope", system-ui, sans-serif',
    titleStyle: { fontFamily: '"Manrope", system-ui, sans-serif', fontWeight: 800, fontSize: 18, letterSpacing: '-0.02em' },
    background: p => `radial-gradient(90% 60% at 50% -20%, ${p.primary}2e, transparent 70%)`,
    card: () => ({ boxShadow: '0 10px 24px -18px rgba(2,12,24,.7)' }),
    button: () => ({ border: 'none' }),
  },
}
