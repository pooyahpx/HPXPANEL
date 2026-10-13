import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { SubTheme, SubThemeMode } from '@/service/api'
import { Eye, Moon, Sun } from 'lucide-react'
import type { CSSProperties, ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { modeText, st, themeText } from '../lib/i18n'
import { SKINS, type Palette, type SkinSpec } from '../lib/skins'

interface ThemePreviewProps {
  theme: SubTheme
  mode: SubThemeMode
  disabled?: boolean
  onModeChange: (mode: SubThemeMode) => void
}

interface Text {
  brand: string
  kicker: string
  heroTitle: string
  heroSubtitle: string
  status: string
  used: string
  remaining: string
  expires: string
  expiresValue: string
  links: string
  copy: string
  qr: string
  apps: string
  appsGet: string
  chart: string
  support: string
  supportButton: string
}

interface Ctx {
  p: Palette
  skin: SkinSpec
  tx: Text
  surface: CSSProperties
  button: CSSProperties
  ghost: CSSProperties
}

const LINKS = [
  { proto: 'VLESS', url: 'vless://3f2a...b91c@hpx.example.com:443?type=ws&security=tls#HPX-1' },
  { proto: 'VMESS', url: 'vmess://eyJhZGQiOiJocHguZXhhbXBsZS5jb20iLCJwb3J0IjoiNDQzIn0=' },
  { proto: 'TROJAN', url: 'trojan://9c1d...e44a@hpx.example.com:443?sni=hpx.example.com#HPX-3' },
]
const APPS = ['Hiddify', 'v2rayN', 'Streisand']
const SHARE: [string, number, string][] = [
  ['Frankfurt · VLESS', 54.2, '22.3 GB'],
  ['Amsterdam · Trojan', 31.6, '13.0 GB'],
  ['Panel / Unknown', 14.2, '5.9 GB'],
]
const SHARE_TITLE = 'Traffic by path'
const BARS = [34, 52, 41, 68, 47, 82, 58, 74, 49, 63, 88, 55]
const MONO = '"JetBrains Mono", ui-monospace, monospace'

const hairline = (p: Palette) => `1px solid ${p.border}`

function Gauge({ ctx, size, thick, glow, label }: { ctx: Ctx; size: number; thick: number; glow?: boolean; label?: boolean }) {
  const { p } = ctx
  const hole = size - thick * 2
  // Translucent card colours (8-digit hex, e.g. nova glass) would show the ring through the hole.
  const holeBg = p.card.length > 7 ? p.bg : p.card
  const fontSize = Math.max(11, hole * 0.26)
  return (
    <div
      className="relative grid shrink-0 place-items-center rounded-full"
      style={{ width: size, height: size, background: `conic-gradient(${p.ok} 0 68%, ${p.muted} 0)`, filter: glow ? `drop-shadow(0 0 8px ${p.ok}99)` : undefined }}
    >
      <div className="grid place-items-center rounded-full text-center" style={{ width: hole, height: hole, background: holeBg }}>
        <div>
          <div className="font-bold" style={{ fontFamily: ctx.skin.titleStyle.fontFamily, fontSize, lineHeight: 1, letterSpacing: '-0.02em' }}>
            68%
          </div>
          {label && <div className="mt-0.5 text-[8px] tracking-widest uppercase opacity-60">{ctx.tx.used}</div>}
        </div>
      </div>
    </div>
  )
}

function Chart({ ctx, radius, glow, thin }: { ctx: Ctx; radius: number; glow?: boolean; thin?: boolean }) {
  const { p } = ctx
  return (
    <div className="flex h-28 items-end gap-1.5 px-3 pt-3 pb-2" style={{ backgroundImage: `linear-gradient(${p.fg}10 1px, transparent 1px)`, backgroundSize: '100% 25%' }}>
      {BARS.map((h, i) => (
        <span
          key={i}
          className="block flex-1"
          style={{
            height: `${h}%`,
            maxWidth: thin ? 8 : undefined,
            borderRadius: radius,
            background: i === 10 ? p.accent : `linear-gradient(180deg, ${p.primary}, ${p.primary}55)`,
            boxShadow: glow ? `0 0 10px ${p.primary}88` : undefined,
          }}
        />
      ))}
    </div>
  )
}

function Btn({ ctx, children, ghost, className }: { ctx: Ctx; children: ReactNode; ghost?: boolean; className?: string }) {
  return (
    <span className={cn('inline-flex items-center justify-center px-3 py-1.5 text-[10px] font-bold whitespace-nowrap', className)} style={ghost ? ctx.ghost : ctx.button}>
      {children}
    </span>
  )
}

function AppRow({ ctx, cardStyle, grid = 'grid-cols-3', compact }: { ctx: Ctx; cardStyle: CSSProperties; grid?: string; compact?: boolean }) {
  const { p, tx } = ctx
  return (
    <div className={cn('grid gap-2.5', grid)}>
      {APPS.map((app, i) => (
        <div key={app} className={cn('flex items-center gap-2.5', compact ? 'p-2' : 'p-3')} style={cardStyle}>
          <span className="grid size-8 shrink-0 place-items-center text-xs font-bold" style={{ background: `${p.primary}22`, color: p.primary, borderRadius: ctx.skin.btnRadius === 999 ? 10 : ctx.skin.btnRadius }}>
            {app[0]}
          </span>
          <div className="min-w-0 flex-1">
            <div className="truncate text-[11px] font-bold">{app}</div>
            <div className="text-[9px] opacity-60">{['Android', 'Windows', 'iOS'][i]}</div>
          </div>
          <Btn ctx={ctx} className="!px-2 !py-1 !text-[9px]">
            {tx.appsGet}
          </Btn>
        </div>
      ))}
    </div>
  )
}

const SectionTitle = ({ children, style }: { children: ReactNode; style?: CSSProperties }) => (
  <div className="mb-2 text-xs font-bold" style={style}>
    {children}
  </div>
)

const Support = ({ ctx, style, className }: { ctx: Ctx; style?: CSSProperties; className?: string }) => (
  <div className={cn('flex flex-wrap items-center justify-between gap-3 text-[11px]', className)} style={style}>
    <span className="opacity-70">{ctx.tx.support}</span>
    <Btn ctx={ctx}>{ctx.tx.supportButton}</Btn>
  </div>
)

/* ------------------------------ TERMINAL ------------------------------ */
function TerminalLayout({ ctx }: { ctx: Ctx }) {
  const { p, tx, surface } = ctx
  const hard: CSSProperties = { ...surface, boxShadow: `4px 4px 0 ${p.border}` }
  return (
    <div className="space-y-4 p-5 md:p-7" style={{ fontFamily: MONO }}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-[11px] font-bold tracking-[0.18em] uppercase" style={{ color: p.primary }}>
          <span className="block size-5" style={{ background: p.primary, border: `2px solid ${p.border}`, boxShadow: `2px 2px 0 ${p.border}` }} />
          {tx.brand}
        </div>
        <span className="px-2 py-0.5 text-[9px] font-bold tracking-widest uppercase" style={{ border: `2px solid ${p.border}`, color: p.primary }}>
          secure // sub
        </span>
      </div>
      <div>
        <div className="text-[9px] font-bold tracking-[0.16em] uppercase" style={{ color: p.primary }}>
          {tx.kicker}
        </div>
        <div className="mt-1 text-2xl md:text-3xl" style={ctx.skin.titleStyle}>
          {tx.heroTitle}
        </div>
        <div className="mt-1 text-[11px] opacity-60">@{tx.heroSubtitle}</div>
        <div className="mt-3 flex max-w-xl items-center gap-2 p-1.5" style={{ ...surface, boxShadow: `3px 3px 0 ${p.border}` }}>
          <span className="truncate ps-2 text-[10px] opacity-70">https://sub.example.com/sub/aB3dE9</span>
          <Btn ctx={ctx} className="ms-auto">
            {tx.copy}
          </Btn>
          <Btn ctx={ctx} ghost>
            {tx.qr}
          </Btn>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-[1.7fr_0.9fr]">
        <div className="p-4" style={hard}>
          <div className="flex items-start justify-between">
            <div className="text-2xl font-bold tracking-wider uppercase" style={{ color: p.ok }}>
              {tx.status} ■
            </div>
            <div className="text-end text-[9px] tracking-widest uppercase opacity-60">
              {tx.expires}
              <div className="text-sm font-bold opacity-100" style={{ color: p.fg }}>
                {tx.expiresValue}
              </div>
            </div>
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-5">
            <Gauge ctx={ctx} size={110} thick={14} label />
            <div className="grid min-w-[160px] flex-1 gap-2">
              {[
                [tx.used, '41.2 GB'],
                ['Limit', '60 GB'],
                [tx.remaining, '18.8 GB'],
              ].map(([k, v]) => (
                <div key={k} className="flex items-baseline justify-between px-2.5 py-1.5" style={{ border: hairline(p), background: `${p.muted}88` }}>
                  <span className="text-[9px] tracking-widest uppercase opacity-60">{k}</span>
                  <span className="text-sm font-bold">{v}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="mt-4 h-3" style={{ background: p.muted, border: hairline(p) }}>
            <div className="h-full w-[68%]" style={{ background: p.ok }} />
          </div>
        </div>
        <div className="grid content-start gap-3">
          {[
            ['01', 'Lifetime', '212.4 GB'],
            ['02', tx.expires, '2026-11-02'],
            ['03', 'Last online', '2 min ago'],
          ].map(([n, k, v]) => (
            <div key={n} className="p-3" style={{ ...surface, boxShadow: `4px 4px 0 ${p.border}` }}>
              <div className="text-[9px] tracking-widest uppercase opacity-60">
                {n} / {k}
              </div>
              <div className="mt-1 text-lg font-bold">{v}</div>
            </div>
          ))}
        </div>
      </div>

      <div style={hard}>
        <div className="px-3 py-2 text-xs font-bold" style={{ borderBottom: hairline(p) }}>
          {tx.links}
        </div>
        <div className="space-y-2 p-3">
          {LINKS.map(l => (
            <div key={l.proto} className="flex items-center gap-2 p-1.5" style={{ border: `2px solid ${p.border}`, background: `${p.muted}66` }}>
              <span className="px-2 py-0.5 text-[9px] font-bold" style={{ border: `2px solid ${p.border}`, background: `${p.primary}2a`, color: p.primary }}>
                {l.proto}
              </span>
              <span className="min-w-0 flex-1 truncate text-[10px] opacity-80">{l.url}</span>
              <Btn ctx={ctx}>{tx.copy}</Btn>
              <Btn ctx={ctx}>{tx.qr}</Btn>
            </div>
          ))}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="p-3" style={hard}>
          <SectionTitle>{tx.apps}</SectionTitle>
          <AppRow ctx={ctx} cardStyle={{ border: hairline(p), background: `${p.muted}66` }} grid="grid-cols-1" compact />
        </div>
        <div style={hard}>
          <div className="px-3 pt-3 text-xs font-bold">{tx.chart}</div>
          <Chart ctx={ctx} radius={0} />
        </div>
      </div>
      <Support ctx={ctx} className="pt-1" style={{ borderTop: `2px dashed ${p.border}`, paddingTop: 14 }} />
    </div>
  )
}

/* ------------------------------ AURORA ------------------------------ */
function AuroraLayout({ ctx }: { ctx: Ctx }) {
  const { p, tx, surface } = ctx
  const serif: CSSProperties = { fontFamily: '"Playfair Display", Georgia, serif', fontStyle: 'italic', fontWeight: 500 }
  const soft: CSSProperties = { ...surface, borderRadius: 24 }
  return (
    <div className="mx-auto max-w-4xl space-y-8 px-6 py-8 md:px-10 md:py-12">
      <div className="flex items-center justify-between pb-4" style={{ borderBottom: `1px solid ${p.accent}55` }}>
        <div className="flex items-center gap-3 text-sm font-semibold tracking-[0.34em]">
          <span className="block size-4 rotate-45" style={{ background: `linear-gradient(135deg, ${p.accent}, ${p.primary})`, boxShadow: `0 0 0 4px ${p.accent}22` }} />
          {tx.brand}
        </div>
        <span className="text-[10px] font-semibold tracking-[0.22em]" style={{ color: p.accent }}>
          SECURE // SUB
        </span>
      </div>

      <div>
        <div className="text-sm tracking-[0.24em]" style={{ ...serif, color: p.accent }}>
          {tx.kicker}
        </div>
        <h3 className="mt-2 text-5xl leading-none md:text-7xl" style={{ ...serif, letterSpacing: '-0.02em' }}>
          {tx.heroTitle}
        </h3>
        <span className="mt-5 block h-[2px] w-24" style={{ background: `linear-gradient(90deg, ${p.accent}, transparent)` }} />
        <div className="mt-3 text-sm opacity-70">@{tx.heroSubtitle}</div>
        <div className="mt-5 flex items-center gap-3 rounded-full py-2 ps-6 pe-2" style={{ ...surface, borderRadius: 999 }}>
          <span className="truncate text-xs opacity-70">https://sub.example.com/sub/aB3dE9</span>
          <Btn ctx={ctx} className="ms-auto !px-5">
            {tx.copy}
          </Btn>
          <Btn ctx={ctx} ghost>
            {tx.qr}
          </Btn>
        </div>
      </div>

      <div className="grid items-center gap-8 p-8 md:grid-cols-[auto_1fr] md:p-10" style={{ ...soft, borderRadius: 32 }}>
        <Gauge ctx={ctx} size={170} thick={9} label />
        <div>
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <div className="text-5xl" style={{ ...serif, color: p.ok }}>
              {tx.status}
            </div>
            <div className="text-end text-[10px] font-semibold tracking-[0.18em] uppercase opacity-70">
              {tx.expires}
              <div className="text-xl normal-case" style={{ ...serif, color: p.accent }}>
                {tx.expiresValue}
              </div>
            </div>
          </div>
          <div className="mt-4">
            {[
              [tx.used, '41.2 GB'],
              ['Limit', '60 GB'],
              [tx.remaining, '18.8 GB'],
            ].map(([k, v]) => (
              <div key={k} className="flex items-baseline justify-between py-2.5" style={{ borderBottom: `1px solid ${p.accent}33` }}>
                <span className="text-[10px] font-semibold tracking-[0.18em] uppercase opacity-60">{k}</span>
                <span className="text-xl" style={serif}>
                  {v}
                </span>
              </div>
            ))}
          </div>
          <div className="mt-4 h-1.5 rounded-full" style={{ background: p.muted }}>
            <div className="h-full w-[68%] rounded-full" style={{ background: p.ok }} />
          </div>
        </div>
      </div>

      <div className="grid overflow-hidden md:grid-cols-3" style={{ border: `1px solid ${p.accent}44`, borderRadius: 28, background: p.card }}>
        {[
          ['Lifetime', '212.4 GB'],
          [tx.expires, '2026-11-02'],
          ['Last online', '2 min ago'],
        ].map(([k, v], i) => (
          <div key={k} className="px-7 py-6" style={{ borderInlineStart: i ? `1px solid ${p.accent}33` : undefined }}>
            <div className="text-[10px] font-semibold tracking-[0.18em] uppercase opacity-60">{k}</div>
            <div className="mt-1 text-2xl" style={serif}>
              {v}
            </div>
          </div>
        ))}
      </div>

      <div className="space-y-4">
        <h4 className="text-2xl" style={serif}>
          {tx.links}
        </h4>
        {LINKS.map(l => (
          <div key={l.proto} className="grid grid-cols-[1fr_auto_auto] items-center gap-x-2 gap-y-2 p-5" style={soft}>
            <span className="w-fit rounded-full px-3 py-1 text-[10px] font-semibold tracking-[0.12em]" style={{ border: `1px solid ${p.primary}88`, background: `${p.primary}1f`, color: p.primary }}>
              {l.proto}
            </span>
            <Btn ctx={ctx} ghost>
              {tx.copy}
            </Btn>
            <Btn ctx={ctx} ghost>
              {tx.qr}
            </Btn>
            <span className="col-span-3 truncate text-[11px] opacity-75" style={{ fontFamily: MONO }}>
              {l.url}
            </span>
          </div>
        ))}
      </div>

      <div className="space-y-3">
        <h4 className="text-2xl" style={serif}>
          {tx.apps}
        </h4>
        <AppRow ctx={ctx} cardStyle={soft} />
      </div>

      <div style={soft}>
        <div className="px-6 pt-5 text-lg" style={serif}>
          {tx.chart}
        </div>
        <Chart ctx={ctx} radius={999} thin />
      </div>
      <Support ctx={ctx} style={{ borderTop: `1px solid ${p.accent}44`, paddingTop: 20 }} />
    </div>
  )
}

/* ------------------------------ NOVA ------------------------------ */
function NovaLayout({ ctx }: { ctx: Ctx }) {
  const { p, tx, surface } = ctx
  const glass: CSSProperties = { ...surface, borderRadius: 34 }
  const pill: CSSProperties = { ...surface, borderRadius: 999 }
  const grad: CSSProperties = { background: `linear-gradient(120deg, ${p.primary}, ${p.accent})` }
  return (
    <div className="relative">
      <div className="mx-auto max-w-[560px] space-y-5 px-5 py-8 text-center">
        <div className="flex flex-col items-center gap-2">
          <span className="block size-9 rounded-full" style={{ ...grad, boxShadow: `0 8px 22px -4px ${p.primary}b0` }} />
          <div className="text-sm font-extrabold tracking-[0.1em]" style={{ fontFamily: '"Syne", system-ui, sans-serif' }}>
            {tx.brand}
          </div>
        </div>
        <div>
          <h3
            className="text-4xl leading-none"
            style={{ ...ctx.skin.titleStyle, fontSize: 40, fontWeight: 800, background: `linear-gradient(100deg, ${p.fg} 30%, ${p.primary} 70%, ${p.accent})`, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent' }}
          >
            {tx.heroTitle}
          </h3>
          <div className="mt-3 flex flex-wrap items-center justify-center gap-2 text-[10px] font-bold">
            <span className="px-3 py-1" style={pill}>
              @{tx.heroSubtitle}
            </span>
            <span className="px-3 py-1" style={{ ...pill, color: p.ok }}>
              ● Online
            </span>
          </div>
          <div className="mx-auto mt-4 flex items-center gap-2 p-1.5 ps-5" style={pill}>
            <span className="truncate text-[11px] opacity-70">https://sub.example.com/sub/aB3dE9</span>
            <Btn ctx={ctx} className="ms-auto">
              {tx.copy}
            </Btn>
          </div>
        </div>

        <div className="flex flex-col items-center gap-5 px-6 py-7" style={glass}>
          <div className="text-3xl font-extrabold" style={{ color: p.ok, fontFamily: '"Syne", system-ui, sans-serif' }}>
            {tx.status}
          </div>
          <Gauge ctx={ctx} size={150} thick={13} glow label />
          <div className="grid w-full grid-cols-3 gap-2">
            {[
              [tx.used, '41.2 GB'],
              [tx.remaining, '18.8 GB'],
              [tx.expires, tx.expiresValue],
            ].map(([k, v]) => (
              <div key={k} className="px-2 py-3" style={pill}>
                <div className="text-[8px] tracking-widest uppercase opacity-60">{k}</div>
                <div className="text-xs font-bold">{v}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="flex flex-wrap justify-center gap-2.5">
          {[
            ['Lifetime', '212.4 GB'],
            ['Last online', '2 min ago'],
          ].map(([k, v]) => (
            <div key={k} className="min-w-[180px] flex-1 px-5 py-3" style={pill}>
              <div className="text-[8px] tracking-widest uppercase opacity-60">{k}</div>
              <div className="text-sm font-bold">{v}</div>
            </div>
          ))}
        </div>

        <div className="space-y-2.5 p-4 text-start" style={glass}>
          <SectionTitle style={{ textAlign: 'center' }}>{tx.links}</SectionTitle>
          {LINKS.map(l => (
            <div key={l.proto} className="flex items-center gap-2 p-1.5 ps-2" style={pill}>
              <span className="rounded-full px-2.5 py-1 text-[9px] font-bold" style={{ background: `${p.primary}30` }}>
                {l.proto}
              </span>
              <span className="min-w-0 flex-1 truncate text-[10px] opacity-70">{l.url}</span>
              <Btn ctx={ctx}>{tx.copy}</Btn>
              <Btn ctx={ctx} ghost>
                {tx.qr}
              </Btn>
            </div>
          ))}
        </div>

        <div style={glass}>
          <div className="px-4 pt-4 text-xs font-bold">{tx.chart}</div>
          <Chart ctx={ctx} radius={999} thin />
        </div>
        <div className="space-y-2.5 text-start">
          <AppRow ctx={ctx} cardStyle={{ ...surface, borderRadius: 30 }} grid="grid-cols-1" compact />
        </div>
        <Support ctx={ctx} className="justify-center text-center" />
      </div>
      <span
        className="pointer-events-none absolute end-5 bottom-5 grid size-16 animate-bounce place-items-center rounded-full text-[8px] font-extrabold tracking-wider uppercase motion-reduce:animate-none"
        style={{ background: `radial-gradient(circle at 32% 26%, ${p.ok}, ${p.ok}66 64%, ${p.ok}22)`, boxShadow: `0 0 0 8px ${p.ok}1f, 0 0 36px ${p.ok}88`, color: p.onPrimary }}
      >
        {tx.status}
      </span>
    </div>
  )
}

/* ------------------------------ ATLAS ------------------------------ */
function AtlasLayout({ ctx }: { ctx: Ctx }) {
  const { p, tx, surface } = ctx
  const bar: CSSProperties = { ...surface, borderRadius: 10, borderLeft: `3px solid ${p.primary}`, boxShadow: 'none' }
  return (
    <div className="space-y-3 p-4 md:p-5">
      <div className="flex items-center justify-between pb-3" style={{ borderBottom: hairline(p) }}>
        <div className="flex items-center gap-2 text-xs font-bold tracking-[0.14em]">
          <span className="block size-5" style={{ background: p.primary, borderRadius: 6 }} />
          {tx.brand}
        </div>
        <div className="flex items-center gap-2 text-[10px]">
          <span className="px-2 py-0.5" style={{ border: hairline(p), borderRadius: 6 }}>
            secure // sub
          </span>
          <span className="px-2 py-0.5 font-bold" style={{ background: `${p.ok}22`, color: p.ok, borderRadius: 999 }}>
            ● {tx.status}
          </span>
        </div>
      </div>
      <div className="flex flex-wrap items-end justify-between gap-2">
        <div>
          <h3 className="text-2xl font-semibold" style={{ fontFamily: '"Outfit", system-ui, sans-serif' }}>
            {tx.heroTitle}
          </h3>
          <div className="text-[11px] opacity-60" style={{ fontFamily: MONO }}>
            @{tx.heroSubtitle}
          </div>
        </div>
        <div className="flex items-center gap-2 p-1 ps-3" style={{ ...surface, borderRadius: 10, boxShadow: 'none' }}>
          <span className="truncate text-[10px] opacity-70">https://sub.example.com/sub/aB3dE9</span>
          <Btn ctx={ctx}>{tx.copy}</Btn>
          <Btn ctx={ctx} ghost>
            {tx.qr}
          </Btn>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-[230px_1fr]">
        <div className="overflow-hidden" style={{ border: hairline(p), borderTop: `3px solid ${p.primary}`, borderRadius: 12, background: p.card }}>
          {[
            ['01', 'Lifetime', '212.4 GB'],
            ['02', tx.expires, '2026-11-02'],
            ['03', 'Last online', '2 min ago'],
            ['04', tx.remaining, '18.8 GB'],
          ].map(([n, k, v], i) => (
            <div key={n} className="px-3.5 py-2.5" style={{ borderBottom: i < 3 ? hairline(p) : undefined, borderLeft: `3px solid ${p.primary}` }}>
              <div className="text-[9px] font-semibold tracking-[0.06em] uppercase opacity-60">
                {n} / {k}
              </div>
              <div className="text-base font-semibold tabular-nums">{v}</div>
            </div>
          ))}
        </div>

        <div className="space-y-3">
          <div className="p-4" style={bar}>
            <div className="flex flex-wrap items-center gap-5">
              <Gauge ctx={ctx} size={104} thick={11} label />
              <div className="min-w-[200px] flex-1 overflow-hidden" style={{ border: hairline(p), borderRadius: 8 }}>
                {[
                  [tx.used, '41.2 GB'],
                  ['Limit', '60 GB'],
                  [tx.remaining, '18.8 GB'],
                  [tx.expires, tx.expiresValue],
                ].map(([k, v], i) => (
                  <div key={k} className="flex items-baseline justify-between px-3 py-1.5" style={{ background: i % 2 ? `${p.muted}66` : 'transparent', borderBottom: i < 3 ? hairline(p) : undefined }}>
                    <span className="text-[10px] font-semibold tracking-[0.06em] uppercase opacity-60">{k}</span>
                    <span className="text-sm font-semibold tabular-nums">{v}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="mt-3 h-2.5 overflow-hidden rounded-full" style={{ background: p.muted }}>
              <div className="h-full w-[68%]" style={{ background: p.ok }} />
            </div>
          </div>

          <div className="overflow-hidden" style={bar}>
            <div className="flex items-center justify-between px-3 py-2 text-[11px] font-semibold uppercase" style={{ background: `${p.muted}66`, borderBottom: hairline(p) }}>
              <span>{tx.links}</span>
              <span className="text-[9px] tracking-widest opacity-60">protocol / uri / actions</span>
            </div>
            {LINKS.map((l, i) => (
              <div key={l.proto} className="flex items-center gap-2 px-3 py-1.5" style={{ background: i % 2 ? `${p.muted}4d` : 'transparent', borderBottom: i < 2 ? hairline(p) : undefined }}>
                <span className="w-14 rounded px-1.5 py-0.5 text-center text-[9px] font-bold" style={{ border: `1px solid ${p.primary}66`, background: `${p.primary}1f`, color: p.primary }}>
                  {l.proto}
                </span>
                <span className="min-w-0 flex-1 truncate text-[10px] opacity-75" style={{ fontFamily: MONO }}>
                  {l.url}
                </span>
                <Btn ctx={ctx} ghost className="!px-2 !py-1 !text-[9px]">
                  {tx.copy}
                </Btn>
                <Btn ctx={ctx} ghost className="!px-2 !py-1 !text-[9px]">
                  {tx.qr}
                </Btn>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-[1.2fr_1fr]">
        <div style={bar}>
          <div className="px-3 pt-3 text-[11px] font-semibold uppercase">{tx.chart}</div>
          <Chart ctx={ctx} radius={2} />
        </div>
        <div className="p-3" style={bar}>
          <SectionTitle>{tx.apps}</SectionTitle>
          <AppRow ctx={ctx} cardStyle={{ border: hairline(p), borderRadius: 8, background: `${p.muted}55` }} grid="grid-cols-1" compact />
        </div>
      </div>
      <Support ctx={ctx} style={{ borderTop: hairline(p), paddingTop: 12 }} />
    </div>
  )
}

/* ------------------------------ PULSE ------------------------------ */
function PulseLayout({ ctx }: { ctx: Ctx }) {
  const { p, tx, surface } = ctx
  const neon: CSSProperties = { ...surface, border: `1px solid ${p.primary}88`, borderLeft: `3px solid ${p.primary}`, boxShadow: `0 0 0 1px ${p.primary}18, 0 0 26px -10px ${p.primary}aa, inset 0 0 22px -18px ${p.primary}` }
  const display = { fontFamily: '"Space Grotesk", system-ui, sans-serif' }
  return (
    <div className="space-y-4 p-5 md:p-7">
      <style>{`
        @keyframes hpx-shimmer{0%,55%{transform:translateX(-140%) skewX(-20deg)}100%{transform:translateX(160%) skewX(-20deg)}}
        @keyframes hpx-glow{0%,100%{text-shadow:0 0 0 transparent;opacity:1}50%{text-shadow:0 0 22px var(--hpx-glow);opacity:.88}}
      `}</style>
      <div className="flex items-center justify-between pb-3" style={{ borderBottom: `1px solid ${p.primary}40` }}>
        <div className="flex items-center gap-2 text-sm font-bold tracking-[0.18em]" style={display}>
          <span className="block size-6 rounded" style={{ background: `linear-gradient(135deg, ${p.primary}, ${p.accent})`, boxShadow: `0 0 12px ${p.primary}aa` }} />
          {tx.brand}
        </div>
        <span className="flex items-center gap-1.5 text-[10px] font-bold tracking-widest uppercase" style={{ color: p.accent }}>
          <span className="block size-2 animate-pulse rounded-full motion-reduce:animate-none" style={{ background: p.accent, boxShadow: `0 0 8px ${p.accent}` }} />
          live
        </span>
      </div>

      <div>
        <h3
          className="text-4xl leading-none md:text-6xl"
          style={{ ...display, fontWeight: 700, letterSpacing: '-0.035em', background: `linear-gradient(100deg, ${p.fg} 45%, ${p.primary} 80%, ${p.accent})`, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent' }}
        >
          {tx.heroTitle}
        </h3>
        <div className="mt-2 text-[11px] opacity-60" style={{ fontFamily: MONO }}>
          @{tx.heroSubtitle}
        </div>
      </div>

      <div className="grid items-start gap-4 md:grid-cols-[1.35fr_0.85fr]">
        <div className="relative overflow-hidden p-5" style={{ ...neon, borderLeftWidth: 4 }}>
          <span className="absolute -end-10 -top-6 -bottom-6 w-32 -skew-x-[18deg]" style={{ background: `linear-gradient(180deg, ${p.primary}33, ${p.accent}14)` }} />
          <div
            className="relative text-5xl font-bold uppercase motion-safe:animate-[hpx-glow_2.4s_ease-in-out_infinite]"
            style={{ ...display, color: p.ok, letterSpacing: '-0.02em', ['--hpx-glow' as string]: `${p.ok}bb` }}
          >
            {tx.status}
          </div>
          <div className="relative mt-5 flex flex-wrap items-center gap-6">
            <Gauge ctx={ctx} size={190} thick={18} glow label />
            <div className="grid min-w-[150px] flex-1 gap-2">
              {[
                [tx.used, '41.2 GB'],
                [tx.remaining, '18.8 GB'],
                [tx.expires, tx.expiresValue],
              ].map(([k, v], i) => (
                <div key={k} className="px-3 py-2" style={{ border: `1px solid ${p.primary}40`, borderLeft: `3px solid ${p.accent}`, borderRadius: 4, background: `${p.muted}88`, marginInlineStart: i * 12 }}>
                  <div className="text-[9px] tracking-widest uppercase opacity-60">{k}</div>
                  <div className="text-base font-bold" style={display}>
                    {v}
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="relative mt-5 h-2.5 overflow-hidden rounded-full" style={{ background: p.muted }}>
            <div className="h-full w-[68%]" style={{ background: `linear-gradient(90deg, ${p.primary}, ${p.accent})` }} />
          </div>
          <div className="relative mt-4 flex items-center gap-2">
            <span className="relative inline-flex overflow-hidden px-5 py-2 text-xs font-bold" style={ctx.button}>
              {tx.copy}
              <span className="absolute inset-y-0 start-0 w-8 motion-safe:animate-[hpx-shimmer_3.2s_ease-in-out_infinite]" style={{ background: 'rgba(255,255,255,.45)' }} />
            </span>
            <Btn ctx={ctx} ghost>
              {tx.qr}
            </Btn>
          </div>
        </div>

        <div className="grid gap-3 md:pt-8">
          {[
            ['Lifetime', '212.4 GB'],
            [tx.expires, '2026-11-02'],
            ['Last online', '2 min ago'],
          ].map(([k, v], i) => (
            <div key={k} className="p-3.5" style={{ ...surface, border: `1px solid ${p.primary}55`, borderRight: `3px solid ${p.accent}`, boxShadow: `0 0 18px -10px ${p.primary}99`, marginInlineStart: i % 2 ? 22 : 0 }}>
              <div className="text-[9px] tracking-widest uppercase opacity-60">{k}</div>
              <div className="text-xl font-bold" style={{ ...display, color: p.primary }}>
                {v}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div style={neon}>
        <div className="px-4 py-3 text-sm font-bold" style={{ ...display, borderBottom: `1px solid ${p.primary}33` }}>
          {tx.links}
        </div>
        <div className="space-y-2 p-3">
          {LINKS.map(l => (
            <div key={l.proto} className="flex items-center gap-2 p-1.5" style={{ border: `1px solid ${p.primary}40`, borderLeft: `3px solid ${p.accent}`, borderRadius: 6, background: `${p.muted}66` }}>
              <span className="rounded-[3px] px-2 py-0.5 text-[9px] font-bold" style={{ background: `${p.primary}29`, color: p.primary }}>
                {l.proto}
              </span>
              <span className="min-w-0 flex-1 truncate text-[10px] opacity-75" style={{ fontFamily: MONO }}>
                {l.url}
              </span>
              <Btn ctx={ctx} ghost>
                {tx.copy}
              </Btn>
              <Btn ctx={ctx} ghost>
                {tx.qr}
              </Btn>
            </div>
          ))}
        </div>
      </div>

      <div style={{ ...neon, border: `1px solid ${p.primary}`, boxShadow: `0 0 0 1px ${p.primary}59, 0 0 38px -8px ${p.primary}bf, inset 0 0 34px -20px ${p.primary}` }}>
        <div className="px-4 pt-3 text-sm font-bold" style={display}>
          {tx.chart}
        </div>
        <Chart ctx={ctx} radius={2} glow />
      </div>

      <div>
        <SectionTitle style={display}>{tx.apps}</SectionTitle>
        <AppRow ctx={ctx} cardStyle={{ ...surface, borderTop: `2px solid ${p.primary}`, boxShadow: 'none' }} />
      </div>
      <Support ctx={ctx} style={{ borderTop: `1px solid ${p.primary}33`, paddingTop: 14 }} />
    </div>
  )
}

/** Ranked "traffic by path" bars with percentages; the top row is highlighted. */
function ShareBars({ ctx, radius, rowStyle, label }: { ctx: Ctx; radius: number; rowStyle?: CSSProperties; label?: string }) {
  const { p } = ctx
  return (
    <div className="space-y-2.5">
      {SHARE.map(([name, pct, size], i) => (
        <div key={name} className="p-2" style={rowStyle}>
          <div className="flex items-center justify-between gap-2 text-[11px]">
            <span className="flex min-w-0 items-center gap-2 font-semibold">
              <span className="truncate">{name}</span>
              {i === 0 && (
                <span className="shrink-0 px-1.5 py-px text-[8px] font-bold tracking-widest uppercase" style={{ background: p.primary, color: p.onPrimary, borderRadius: Math.min(radius, 6) }}>
                  {label ?? 'Most used'}
                </span>
              )}
            </span>
            <span className="shrink-0 tabular-nums">
              <span className="font-bold">{pct}%</span> <span className="opacity-60">{size}</span>
            </span>
          </div>
          <div className="mt-1.5 h-2 overflow-hidden" style={{ background: p.muted, borderRadius: radius }}>
            <div className="h-full" style={{ width: `${pct}%`, background: i === 0 ? p.primary : `${p.primary}88`, borderRadius: radius }} />
          </div>
        </div>
      ))}
    </div>
  )
}

/* ------------------------------ EMBER ------------------------------ */
function EmberLayout({ ctx }: { ctx: Ctx }) {
  const { p, tx, surface } = ctx
  const display: CSSProperties = { fontFamily: '"Space Grotesk", system-ui, sans-serif' }
  const plate: CSSProperties = { ...surface, borderTop: `3px solid ${p.primary}` }
  return (
    <div className="mx-auto max-w-3xl space-y-3 p-4 md:p-6" style={display}>
      <div className="flex items-center justify-between text-[11px] font-bold tracking-[0.2em] uppercase">
        <span className="flex items-center gap-2">
          <span className="block size-4" style={{ background: p.primary, borderRadius: 2 }} />
          {tx.brand}
        </span>
        <span className="opacity-60">sub // 01</span>
      </div>

      <div className="flex flex-wrap items-center gap-x-5 gap-y-2 px-4 py-3" style={{ background: p.primary, color: p.onPrimary, borderRadius: ctx.skin.radius }}>
        <span className="text-3xl leading-none font-bold uppercase md:text-4xl" style={{ letterSpacing: '-0.02em' }}>
          {tx.status}
        </span>
        <span className="text-xs font-bold tracking-widest uppercase opacity-80">
          {tx.expires} · {tx.expiresValue}
        </span>
        <span className="ms-auto text-2xl font-bold tabular-nums">68%</span>
      </div>
      <div className="h-2" style={{ background: p.muted }}>
        <div className="h-full w-[68%]" style={{ background: p.accent }} />
      </div>

      <div>
        <h3 className="text-2xl leading-tight font-bold uppercase md:text-3xl" style={{ letterSpacing: '-0.02em' }}>
          {tx.heroTitle}
        </h3>
        <div className="text-[11px] opacity-60" style={{ fontFamily: MONO }}>
          @{tx.heroSubtitle}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 p-2" style={plate}>
        <span className="min-w-0 flex-1 basis-40 truncate ps-1 text-[11px] opacity-70" style={{ fontFamily: MONO }}>
          https://sub.example.com/sub/aB3dE9
        </span>
        <Btn ctx={ctx}>{tx.copy}</Btn>
        <Btn ctx={ctx} ghost>
          {tx.qr}
        </Btn>
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {[
          [tx.used, '41.2 GB'],
          [tx.remaining, '18.8 GB'],
          ['Lifetime', '212.4 GB'],
          ['Last online', '2 min ago'],
        ].map(([k, v]) => (
          <div key={k} className="p-3" style={plate}>
            <div className="text-[9px] font-bold tracking-widest uppercase opacity-60">{k}</div>
            <div className="mt-0.5 text-lg font-bold tabular-nums">{v}</div>
          </div>
        ))}
      </div>

      <div style={plate}>
        <div className="px-3 py-2 text-xs font-bold tracking-widest uppercase" style={{ borderBottom: hairline(p) }}>
          {tx.links}
        </div>
        <div className="space-y-2 p-3">
          {LINKS.map(l => (
            <div key={l.proto} className="flex flex-wrap items-center gap-2 p-2" style={{ border: hairline(p), background: `${p.muted}66` }}>
              <span className="px-2 py-0.5 text-[9px] font-bold" style={{ background: p.primary, color: p.onPrimary }}>
                {l.proto}
              </span>
              <span className="min-w-0 flex-1 basis-32 truncate text-[10px] opacity-75" style={{ fontFamily: MONO }}>
                {l.url}
              </span>
              <Btn ctx={ctx}>{tx.copy}</Btn>
              <Btn ctx={ctx} ghost>
                {tx.qr}
              </Btn>
            </div>
          ))}
        </div>
      </div>

      <div className="p-3" style={plate}>
        <SectionTitle>{SHARE_TITLE}</SectionTitle>
        <ShareBars ctx={ctx} radius={1} />
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <div className="p-3" style={plate}>
          <SectionTitle>{tx.apps}</SectionTitle>
          <AppRow ctx={ctx} cardStyle={{ border: hairline(p), background: `${p.muted}55` }} grid="grid-cols-1" compact />
        </div>
        <div style={plate}>
          <div className="px-3 pt-3 text-xs font-bold">{tx.chart}</div>
          <Chart ctx={ctx} radius={1} />
        </div>
      </div>
      <Support ctx={ctx} style={{ borderTop: hairline(p), paddingTop: 12 }} />
    </div>
  )
}

/* ------------------------------ FOLIO ------------------------------ */
function FolioLayout({ ctx }: { ctx: Ctx }) {
  const { p, tx } = ctx
  const rule = `1px solid ${p.fg}`
  return (
    <div className="mx-auto max-w-4xl space-y-6 p-5 md:p-8" style={{ fontFamily: '"Outfit", system-ui, sans-serif' }}>
      <div className="flex items-center justify-between pb-2 text-[11px] font-semibold tracking-[0.14em] uppercase" style={{ borderBottom: rule }}>
        <span>{tx.brand}</span>
        <span className="opacity-60">No. 01 — {tx.kicker}</span>
      </div>

      <div className="grid items-start gap-4 md:grid-cols-[1fr_auto] md:gap-8">
        <div>
          <h3 className="text-5xl md:text-7xl" style={ctx.skin.titleStyle}>
            {tx.heroTitle}
          </h3>
          <div className="mt-3 text-sm opacity-60">@{tx.heroSubtitle}</div>
        </div>
        <div className="md:text-end">
          <span className="inline-block px-3 py-1 text-xs font-bold tracking-[0.18em] uppercase" style={{ background: p.primary, color: p.onPrimary }}>
            {tx.status}
          </span>
          <div className="mt-2 text-[10px] tracking-widest uppercase opacity-60">{tx.expires}</div>
          <div className="text-2xl font-bold tabular-nums">{tx.expiresValue}</div>
        </div>
      </div>

      <div style={{ borderTop: rule }}>
        <div className="flex items-center justify-between py-1.5 text-[10px] font-semibold tracking-widest uppercase opacity-70" style={{ borderBottom: hairline(p) }}>
          <span>
            {tx.used} 41.2 GB / 60 GB
          </span>
          <span>68%</span>
        </div>
        <div className="h-1.5" style={{ background: p.muted }}>
          <div className="h-full w-[68%]" style={{ background: p.primary }} />
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4" style={{ borderTop: rule, borderBottom: hairline(p) }}>
        {[
          [tx.used, '41.2 GB'],
          [tx.remaining, '18.8 GB'],
          ['Lifetime', '212.4 GB'],
          ['Last online', '2 min ago'],
        ].map(([k, v], i) => (
          <div key={k} className="px-3 py-3" style={{ borderInlineStart: i ? hairline(p) : undefined }}>
            <div className="text-[9px] font-semibold tracking-widest uppercase opacity-60">{k}</div>
            <div className="text-xl font-bold tabular-nums">{v}</div>
          </div>
        ))}
      </div>

      <div>
        <div className="mb-1 flex items-center justify-between text-xs font-bold tracking-widest uppercase">
          <span>{tx.links}</span>
          <span className="opacity-50">03</span>
        </div>
        <div style={{ borderTop: rule }}>
          {LINKS.map((l, i) => (
            <div key={l.proto} className="grid grid-cols-[auto_1fr_auto] items-center gap-x-3 gap-y-1.5 py-2" style={{ borderBottom: hairline(p) }}>
              <span className="text-[10px] opacity-50 tabular-nums">0{i + 1}</span>
              <span className="text-[11px] font-bold tracking-widest" style={{ color: p.primary }}>
                {l.proto}
              </span>
              <span className="flex gap-1.5">
                <Btn ctx={ctx} className="!px-2.5 !py-1">
                  {tx.copy}
                </Btn>
                <Btn ctx={ctx} ghost className="!px-2.5 !py-1">
                  {tx.qr}
                </Btn>
              </span>
              <span className="col-span-3 truncate text-[10px] opacity-70" style={{ fontFamily: MONO }}>
                {l.url}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div>
        <div className="mb-2 text-xs font-bold tracking-widest uppercase">{SHARE_TITLE}</div>
        <div style={{ borderTop: rule }} className="pt-3">
          <ShareBars ctx={ctx} radius={0} />
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <div>
          <div className="mb-1 text-xs font-bold tracking-widest uppercase">{tx.apps}</div>
          <div className="pt-2" style={{ borderTop: rule }}>
            <AppRow ctx={ctx} cardStyle={{ border: hairline(p) }} grid="grid-cols-1" compact />
          </div>
        </div>
        <div>
          <div className="mb-1 text-xs font-bold tracking-widest uppercase">{tx.chart}</div>
          <div style={{ borderTop: rule }}>
            <Chart ctx={ctx} radius={0} thin />
          </div>
        </div>
      </div>
      <Support ctx={ctx} style={{ borderTop: rule, paddingTop: 12 }} />
    </div>
  )
}

/* ------------------------------ HARBOR ------------------------------ */
function HarborLayout({ ctx }: { ctx: Ctx }) {
  const { p, tx, surface } = ctx
  const card: CSSProperties = { ...surface, borderRadius: 16 }
  return (
    <div className="mx-auto max-w-3xl space-y-4 p-4 md:p-6" style={{ fontFamily: '"Manrope", system-ui, sans-serif' }}>
      <div className="flex items-center justify-between">
        <span className="flex items-center gap-2 text-sm font-extrabold tracking-[0.1em]">
          <span className="block size-6" style={{ background: p.primary, borderRadius: 9 }} />
          {tx.brand}
        </span>
        <span className="px-2.5 py-1 text-[10px] font-bold" style={{ background: `${p.ok}22`, color: p.ok, borderRadius: 999 }}>
          ● {tx.status}
        </span>
      </div>

      <div>
        <h3 className="text-2xl font-extrabold md:text-3xl" style={{ letterSpacing: '-0.02em' }}>
          {tx.heroTitle}
        </h3>
        <div className="text-xs opacity-60">@{tx.heroSubtitle}</div>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {[
          [tx.used, '41.2 GB'],
          [tx.remaining, '18.8 GB'],
          [tx.expires, tx.expiresValue],
        ].map(([k, v]) => (
          <div key={k} className="px-4 py-3" style={card}>
            <div className="text-[10px] font-bold tracking-widest uppercase opacity-60">{k}</div>
            <div className="mt-0.5 text-xl font-extrabold tabular-nums">{v}</div>
          </div>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-5 p-5" style={card}>
        <Gauge ctx={ctx} size={120} thick={12} label />
        <div className="min-w-[200px] flex-1 space-y-3">
          <div className="text-2xl font-extrabold" style={{ color: p.ok }}>
            {tx.status}
          </div>
          <div className="h-2.5 overflow-hidden rounded-full" style={{ background: p.muted }}>
            <div className="h-full w-[68%] rounded-full" style={{ background: p.ok }} />
          </div>
          <div className="flex flex-wrap items-center gap-2 p-1.5 ps-3" style={{ border: hairline(p), borderRadius: 12, background: `${p.muted}66` }}>
            <span className="min-w-0 flex-1 basis-32 truncate text-[10px] opacity-70" style={{ fontFamily: MONO }}>
              https://sub.example.com/sub/aB3dE9
            </span>
            <Btn ctx={ctx}>{tx.copy}</Btn>
            <Btn ctx={ctx} ghost>
              {tx.qr}
            </Btn>
          </div>
        </div>
      </div>

      <div className="space-y-2.5 p-4" style={card}>
        <SectionTitle>{tx.links}</SectionTitle>
        {LINKS.map(l => (
          <div key={l.proto} className="flex flex-wrap items-center gap-2 p-2" style={{ border: hairline(p), borderRadius: 12, background: `${p.muted}55` }}>
            <span className="px-2.5 py-0.5 text-[9px] font-extrabold" style={{ background: `${p.primary}26`, color: p.primary, borderRadius: 999 }}>
              {l.proto}
            </span>
            <span className="min-w-0 flex-1 basis-32 truncate text-[10px] opacity-75" style={{ fontFamily: MONO }}>
              {l.url}
            </span>
            <Btn ctx={ctx}>{tx.copy}</Btn>
            <Btn ctx={ctx} ghost>
              {tx.qr}
            </Btn>
          </div>
        ))}
      </div>

      <div className="p-4" style={card}>
        <SectionTitle>{SHARE_TITLE}</SectionTitle>
        <ShareBars ctx={ctx} radius={999} rowStyle={{ borderRadius: 12 }} />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="p-4" style={card}>
          <SectionTitle>{tx.apps}</SectionTitle>
          <AppRow ctx={ctx} cardStyle={{ border: hairline(p), borderRadius: 12, background: `${p.muted}55` }} grid="grid-cols-1" compact />
        </div>
        <div style={card}>
          <div className="px-4 pt-4 text-xs font-bold">{tx.chart}</div>
          <Chart ctx={ctx} radius={6} thin />
        </div>
      </div>
      <Support ctx={ctx} style={{ borderTop: hairline(p), paddingTop: 12 }} />
    </div>
  )
}

const LAYOUTS: Record<SubTheme, (props: { ctx: Ctx }) => ReactNode> = {
  terminal: TerminalLayout,
  aurora: AuroraLayout,
  nova: NovaLayout,
  atlas: AtlasLayout,
  pulse: PulseLayout,
  ember: EmberLayout,
  folio: FolioLayout,
  harbor: HarborLayout,
}

const MODES: { value: SubThemeMode; icon: typeof Sun }[] = [
  { value: 'dark', icon: Moon },
  { value: 'light', icon: Sun },
]

/** Large, detailed, live mock of the public subscription page for the draft skin and mode. */
export function ThemePreview({ theme, mode, disabled, onModeChange }: ThemePreviewProps) {
  const { t } = useTranslation()
  const skin = SKINS[theme]
  const p = skin[mode]
  const bw = skin.borderWidth

  const tx: Text = {
    brand: st(t, 'subTheme.preview.mock.brand', 'HPXPANEL'),
    kicker: st(t, 'subTheme.preview.mock.kicker', 'Subscription'),
    heroTitle: st(t, 'subTheme.preview.mock.heroTitle', 'Your subscription'),
    heroSubtitle: st(t, 'subTheme.preview.mock.heroSubtitle', 'demo_user - Premium plan'),
    status: st(t, 'subTheme.preview.mock.status', 'Active'),
    used: st(t, 'subTheme.preview.mock.used', 'Used'),
    remaining: st(t, 'subTheme.preview.mock.remaining', 'Remaining'),
    expires: st(t, 'subTheme.preview.mock.expires', 'Expires'),
    expiresValue: st(t, 'subTheme.preview.mock.expiresValue', '23 days'),
    links: st(t, 'subTheme.preview.mock.links', 'Connection links'),
    copy: st(t, 'subTheme.preview.mock.copy', 'Copy'),
    qr: st(t, 'subTheme.preview.mock.qr', 'QR'),
    apps: st(t, 'subTheme.preview.mock.apps', 'Recommended apps'),
    appsGet: st(t, 'subTheme.preview.mock.appsGet', 'Get'),
    chart: st(t, 'subTheme.preview.mock.chart', 'Usage, last 7 days'),
    support: st(t, 'subTheme.preview.mock.support', 'Need help? Contact support'),
    supportButton: st(t, 'subTheme.preview.mock.supportButton', 'Support'),
  }

  const surface: CSSProperties = { border: `${bw}px solid ${p.border}`, borderRadius: skin.radius, background: p.card, ...skin.card?.(p) }
  const button: CSSProperties = { background: p.primary, color: p.onPrimary, borderRadius: skin.btnRadius, border: `${bw}px solid ${p.border}`, ...skin.button?.(p) }
  const ghost: CSSProperties = { background: 'transparent', color: p.fg, borderRadius: skin.btnRadius, border: `${bw}px solid ${p.border}`, boxShadow: 'none' }
  const ctx: Ctx = { p, skin, tx, surface, button, ghost }
  const Layout = LAYOUTS[theme]
  const title = st(t, 'subTheme.preview.title', 'Preview')

  return (
    <section className="space-y-3" aria-labelledby="sub-theme-preview-title">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="space-y-0.5">
          <div className="flex flex-wrap items-center gap-2">
            <Eye className="text-primary size-5" aria-hidden="true" />
            <h2 id="sub-theme-preview-title" className="font-display text-lg font-bold tracking-tight">
              {title}
            </h2>
            <Badge variant="blue" className="shadow-none normal-case">
              {st(t, 'subTheme.preview.skinBadge', '{{name}} skin', { name: themeText(t, theme, 'name') })}
            </Badge>
          </div>
          <p className="text-muted-foreground max-w-2xl text-xs leading-relaxed">
            {st(t, 'subTheme.preview.subtitle', 'This is how the public subscription page will look for your users with the selected skin and mode. Save to apply it.')}
          </p>
        </div>
        <div role="radiogroup" aria-label={st(t, 'subTheme.preview.modeLabel', 'Preview mode')} className="grid grid-cols-2 gap-1.5">
          {MODES.map(({ value, icon: Icon }) => {
            const active = mode === value
            return (
              <button
                key={value}
                type="button"
                role="radio"
                aria-checked={active}
                disabled={disabled}
                onClick={() => onModeChange(value)}
                className={cn(
                  'flex items-center justify-center gap-1.5 border-2 px-3 py-1.5 text-xs font-semibold transition-colors',
                  'focus-visible:ring-ring focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none disabled:opacity-60',
                  active ? 'border-primary bg-primary text-primary-foreground' : 'border-border bg-muted/40 hover:border-primary/60',
                )}
              >
                <Icon className="size-3.5" aria-hidden="true" />
                {modeText(t, value)}
              </button>
            )
          })}
        </div>
      </div>

      <div className="border-border bg-card overflow-hidden border-2 shadow-lg" dir="ltr">
        <div className="bg-muted/60 flex items-center gap-2 border-b px-3 py-2" aria-hidden="true">
          <span className="flex gap-1.5">
            {['#ff5f57', '#febc2e', '#28c840'].map(c => (
              <span key={c} className="block size-2.5 rounded-full" style={{ background: c }} />
            ))}
          </span>
          <span className="bg-background/70 text-muted-foreground mx-auto w-full max-w-md truncate border px-3 py-0.5 text-center font-mono text-[10px]">https://sub.example.com/sub/aB3dE9</span>
          <span className="w-10" />
        </div>
        <div
          key={`${theme}-${mode}`}
          aria-label={title}
          className="relative min-h-[420px] overflow-x-auto transition-colors duration-300 [&>*]:min-w-0"
          style={{ background: p.bg, backgroundImage: skin.background?.(p), backgroundSize: skin.backgroundSize, color: p.fg, fontFamily: skin.fontFamily }}
        >
          <Layout ctx={ctx} />
        </div>
      </div>
    </section>
  )
}
