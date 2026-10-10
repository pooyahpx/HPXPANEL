import { cn } from '@/lib/utils'
import type { SubTheme, SubThemeMode } from '@/service/api'
import type { ComponentType, CSSProperties, ReactNode } from 'react'
import { SKINS, type Palette, type SkinSpec } from '../lib/skins'

interface ThemeMockProps {
  theme: SubTheme
  mode: SubThemeMode
  className?: string
}

interface MockCtx {
  p: Palette
  skin: SkinSpec
  surface: CSSProperties
  button: CSSProperties
}

/** Conic-gradient ring with a hole; used as the usage gauge in every miniature. */
function Ring({ size, hole, pct = 68, color, track, bg, children }: { size: number; hole: number; pct?: number; color: string; track: string; bg: string; children?: ReactNode }) {
  return (
    <div className="relative grid shrink-0 place-items-center rounded-full" style={{ width: size, height: size, background: `conic-gradient(${color} 0 ${pct}%, ${track} 0)` }}>
      <div className="grid place-items-center rounded-full text-[7px] font-bold" style={{ width: hole, height: hole, background: bg }}>
        {children}
      </div>
    </div>
  )
}

const Bar = ({ w, h = 5, color, radius = 3, className }: { w: number | string; h?: number; color: string; radius?: number; className?: string }) => (
  <span className={cn('block shrink-0', className)} style={{ width: w, height: h, background: color, borderRadius: radius }} />
)

/** Terminal: pixel grid, hard square cards, offset shadows, mono; 2-col status + rail. */
function TerminalMock({ p, skin, surface, button }: MockCtx) {
  return (
    <>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <span className="block size-3" style={{ background: p.primary, border: `2px solid ${p.border}`, boxShadow: `2px 2px 0 ${p.border}` }} />
          <span className="text-[7px] font-bold tracking-[0.18em]">HPXPANEL</span>
        </div>
        <span className="px-1.5 py-px text-[6px] font-bold tracking-widest uppercase" style={{ border: `1px solid ${p.border}`, color: p.primary }}>
          secure // sub
        </span>
      </div>
      <div className="mt-2 text-[10px]" style={skin.titleStyle}>
        &gt; Dashboard_
      </div>
      <div className="mt-2 grid grid-cols-[1.6fr_1fr] gap-2.5">
        <div className="p-2" style={surface}>
          <div className="flex items-center justify-between">
            <span className="text-[8px] font-bold tracking-widest uppercase" style={{ color: p.ok }}>
              ■ Active
            </span>
            <span className="text-[6px] opacity-60">23d</span>
          </div>
          <div className="mt-1.5 flex items-center gap-2">
            <Ring size={34} hole={22} color={p.ok} track={p.muted} bg={p.card}>
              68%
            </Ring>
            <div className="min-w-0 flex-1 space-y-1">
              <Bar w="100%" color={p.muted} radius={0} />
              <Bar w="68%" color={p.ok} radius={0} />
              <Bar w="45%" color={p.muted} radius={0} />
            </div>
          </div>
          <span className="mt-2 inline-block px-2 py-0.5 text-[7px] font-bold uppercase" style={button}>
            Copy URL
          </span>
        </div>
        <div className="flex flex-col gap-1.5">
          {['01', '02', '03'].map(n => (
            <div key={n} className="flex items-center justify-between px-1.5 py-1" style={{ ...surface, boxShadow: `2px 2px 0 ${p.border}` }}>
              <span className="text-[6px] opacity-60">{n} /</span>
              <Bar w={22} h={4} color={p.muted} radius={0} />
            </div>
          ))}
        </div>
      </div>
    </>
  )
}

/** Aurora: editorial single column, big italic serif, gold hairline, soft pills, horizontal metric chips. */
function AuroraMock({ p, skin, surface, button }: MockCtx) {
  return (
    <>
      <div className="flex items-center justify-between pb-1.5" style={{ borderBottom: `1px solid ${p.accent}55` }}>
        <span className="text-[7px] font-semibold tracking-[0.3em]">HPXPANEL</span>
        <span className="block size-2 rotate-45" style={{ background: `linear-gradient(135deg, ${p.accent}, ${p.primary})` }} />
      </div>
      <div className="mt-3 truncate" style={skin.titleStyle}>
        Your dashboard
      </div>
      <span className="mt-1.5 block h-[2px] w-12" style={{ background: `linear-gradient(90deg, ${p.accent}, transparent)` }} />
      <div className="mt-2.5 flex items-center gap-2.5 px-3 py-2" style={surface}>
        <Ring size={30} hole={24} color={p.ok} track={p.muted} bg={p.card}>
          <span style={{ fontSize: 6 }}>68%</span>
        </Ring>
        <span className="text-[9px] italic" style={{ fontFamily: '"Playfair Display", Georgia, serif', color: p.ok }}>
          Active
        </span>
        <span className="ms-auto px-2.5 py-0.5 text-[7px] font-bold" style={button}>
          Copy
        </span>
      </div>
      <div className="mt-2 flex gap-1.5">
        {['Used', 'Left', 'Ends'].map(label => (
          <span key={label} className="flex flex-1 items-center justify-center gap-1 py-1 text-[6px] tracking-widest uppercase" style={{ border: `1px solid ${p.border}`, borderRadius: 999, background: `${p.accent}12` }}>
            <span className="block size-1 rounded-full" style={{ background: p.accent }} />
            {label}
          </span>
        ))}
      </div>
    </>
  )
}

/** Nova: centered glass stack with a gradient mesh, circular mark and a floating orb. */
function NovaMock({ p, skin, surface, button }: MockCtx) {
  return (
    <div className="flex h-full flex-col items-center">
      <span className="block size-4 rounded-full" style={{ background: `linear-gradient(135deg, ${p.primary}, ${p.accent})`, boxShadow: `0 4px 10px -2px ${p.primary}aa` }} />
      <div className="mt-1.5" style={skin.titleStyle}>
        Dashboard
      </div>
      <div className="mt-2 flex w-[78%] flex-col items-center gap-1.5 px-3 py-2" style={surface}>
        <Ring size={38} hole={28} color={p.ok} track={p.muted} bg={p.bg}>
          68%
        </Ring>
        <span className="px-3 py-0.5 text-[7px] font-bold" style={button}>
          Copy URL
        </span>
      </div>
      <div className="mt-1.5 flex w-[78%] gap-1">
        {[0, 1, 2].map(i => (
          <span key={i} className="h-2.5 flex-1" style={{ background: p.muted, borderRadius: 999, border: `1px solid ${p.border}` }} />
        ))}
      </div>
      <span
        className="absolute end-2.5 bottom-2.5 block size-6 rounded-full"
        style={{ background: `radial-gradient(circle at 32% 26%, ${p.ok}, ${p.ok}66 64%, ${p.ok}22)`, boxShadow: `0 0 0 3px ${p.ok}22, 0 0 14px ${p.ok}99` }}
      />
    </div>
  )
}

/** Atlas: dense ops layout; KPI rail on the left, table-like rows on the right. */
function AtlasMock({ p, skin, surface }: MockCtx) {
  return (
    <>
      <div className="flex items-center justify-between pb-1" style={{ borderBottom: `1px solid ${p.border}` }}>
        <div className="flex items-center gap-1.5">
          <span className="block size-2.5" style={{ background: p.primary, borderRadius: 3 }} />
          <span className="text-[7px] font-bold tracking-[0.14em]">HPXPANEL</span>
        </div>
        <span className="px-1.5 text-[6px]" style={{ border: `1px solid ${p.border}`, borderRadius: 4 }}>
          sub
        </span>
      </div>
      <div className="mt-2 grid grid-cols-[27%_1fr] gap-2">
        <div className="overflow-hidden" style={{ border: `1px solid ${p.border}`, borderTop: `2px solid ${p.primary}`, borderRadius: skin.radius, background: p.card }}>
          {[0, 1, 2].map(i => (
            <div key={i} className="px-1.5 py-1" style={{ borderBottom: i < 2 ? `1px solid ${p.border}` : undefined, borderLeft: `2px solid ${p.primary}` }}>
              <Bar w={12} h={2} color={p.muted} />
              <Bar w={24} h={4} color={p.fg} className="mt-0.5 opacity-70" />
            </div>
          ))}
        </div>
        <div className="space-y-1.5">
          <div className="flex items-center gap-2 px-2 py-1.5" style={surface}>
            <Ring size={28} hole={20} color={p.ok} track={p.muted} bg={p.card}>
              <span style={{ fontSize: 6 }}>68</span>
            </Ring>
            <span className="text-[8px] font-semibold" style={{ color: p.ok }}>
              Active
            </span>
            <div className="ms-auto w-10 overflow-hidden" style={{ border: `1px solid ${p.border}`, borderRadius: 4 }}>
              {[0, 1, 2].map(i => (
                <Bar key={i} w="100%" h={3} color={i % 2 ? p.muted : 'transparent'} radius={0} />
              ))}
            </div>
          </div>
          <div className="overflow-hidden" style={{ border: `1px solid ${p.border}`, borderRadius: skin.radius, borderLeft: `3px solid ${p.primary}` }}>
            {[0, 1, 2].map(i => (
              <div key={i} className="flex items-center gap-1.5 px-1.5 py-[3px]" style={{ background: i % 2 ? `${p.muted}` : p.card, borderBottom: i < 2 ? `1px solid ${p.border}` : undefined }}>
                <span className="px-1 text-[5px] font-bold uppercase" style={{ background: `${p.primary}22`, color: p.primary, borderRadius: 3 }}>
                  vless
                </span>
                <Bar w="50%" h={3} color={p.muted} className="flex-1" />
                <Bar w={10} h={5} color={p.primary} radius={3} />
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  )
}

/** Pulse: asymmetric kinetic; oversized gauge, neon edges, shimmer bar, pulse dot. */
function PulseMock({ p, skin, surface, button }: MockCtx) {
  return (
    <>
      <div className="flex items-center justify-between pb-1" style={{ borderBottom: `1px solid ${p.primary}44` }}>
        <div className="flex items-center gap-1.5">
          <span className="block size-3" style={{ background: `linear-gradient(135deg, ${p.primary}, ${p.accent})`, borderRadius: 3, boxShadow: `0 0 8px ${p.primary}aa` }} />
          <span className="text-[7px] font-bold tracking-[0.2em]">HPXPANEL</span>
        </div>
        <span className="flex items-center gap-1 text-[6px] font-bold tracking-widest uppercase" style={{ color: p.accent }}>
          <span className="block size-1.5 animate-pulse rounded-full" style={{ background: p.accent }} />
          live
        </span>
      </div>
      <div className="mt-2 grid grid-cols-[1.35fr_0.85fr] gap-2">
        <div className="relative overflow-hidden p-2" style={{ ...surface, border: `1px solid ${p.primary}88`, borderLeft: `3px solid ${p.primary}` }}>
          <span className="absolute -end-4 -top-2 -bottom-2 w-9 -skew-x-[18deg]" style={{ background: `linear-gradient(180deg, ${p.primary}33, ${p.accent}11)` }} />
          <div className="relative flex items-center gap-2">
            <Ring size={58} hole={42} color={p.primary} track={p.muted} bg={p.card}>
              <span style={{ fontSize: 11, fontFamily: '"Space Grotesk", system-ui, sans-serif', fontWeight: 700 }}>68%</span>
            </Ring>
            <div className="min-w-0 space-y-1">
              <div style={{ ...skin.titleStyle, fontSize: 13, color: p.ok }}>ACTIVE</div>
              <Bar w={34} h={4} color={`linear-gradient(90deg, ${p.primary}, ${p.accent})`} radius={2} />
            </div>
          </div>
          <span className="relative mt-2 block overflow-hidden px-2 py-1 text-center text-[7px] font-bold uppercase" style={button}>
            Copy URL
            <span className="absolute inset-y-0 start-[40%] w-4 -skew-x-[20deg]" style={{ background: 'rgba(255,255,255,.4)' }} />
          </span>
        </div>
        <div className="mt-3 flex flex-col gap-1.5">
          {[0, 1, 2].map(i => (
            <div key={i} className="flex items-center justify-between px-1.5 py-1" style={{ border: `1px solid ${p.primary}55`, borderRight: `2px solid ${p.accent}`, borderRadius: skin.radius, marginInlineStart: i % 2 ? 8 : 0, background: p.card }}>
              <Bar w={14} h={3} color={p.muted} />
              <Bar w={10} h={4} color={p.primary} radius={2} />
            </div>
          ))}
        </div>
      </div>
    </>
  )
}

const MOCKS: Record<SubTheme, ComponentType<MockCtx>> = {
  terminal: TerminalMock,
  aurora: AuroraMock,
  nova: NovaMock,
  atlas: AtlasMock,
  pulse: PulseMock,
}

/** CSS-only miniature of the public subscription page; every skin has a different composition. */
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
  const Mock = MOCKS[theme]

  return (
    <div
      dir="ltr"
      aria-hidden="true"
      className={cn('pointer-events-none relative h-48 w-full overflow-hidden p-3 select-none', className)}
      style={{
        background: p.bg,
        backgroundImage: skin.background?.(p),
        backgroundSize: skin.backgroundSize,
        color: p.fg,
        fontFamily: skin.fontFamily,
      }}
    >
      <Mock p={p} skin={skin} surface={surface} button={button} />
    </div>
  )
}
