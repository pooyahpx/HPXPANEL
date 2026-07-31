import { useEffect, useRef, type CSSProperties } from 'react'

type CursorMode = 'default' | 'pointer' | 'text'

const TRAIL_LEN = 7
const LERP = 0.52
const TRAIL_LERP = 0.36
const SCALE = 2 // each art pixel → 2 screen px

const INTERACTIVE =
  'a,button,[role="button"],[role="menuitem"],[role="option"],[role="tab"],[role="switch"],[role="checkbox"],label,summary,.cursor-pointer,[data-cursor="pointer"]'
const TEXTUAL = 'input,textarea,[contenteditable="true"],[data-cursor="text"]'

function resolveMode(target: EventTarget | null): CursorMode {
  if (!(target instanceof Element)) return 'default'
  if (target.closest(TEXTUAL)) return 'text'
  if (target.closest(INTERACTIVE)) return 'pointer'
  return 'default'
}

/**
 * Real classic "pointing hand" sprite (Windows-style).
 * # = black outline, o = white fill, . = empty
 * Index finger points UP. Hotspot ≈ tip.
 */
const OPEN = [
  '......##......',
  '.....#oo#.....',
  '.....#oo#.....',
  '.....#oo#.....',
  '.....#oo#.....',
  '.....#oo#.....',
  '.....#oo#.....',
  '.....#oo#####.',
  '....#oo#ooo#.#',
  '...#oo#oooo#.#',
  '..#oo#ooooo#.#',
  '.#oo#oooooo#.#',
  '#oo#ooooooo##.',
  '#oo#oooooo#...',
  '.#o#oooooo#...',
  '..##o#ooo#....',
  '....#o#o#.....',
  '.....#o#......',
  '......#.......',
]

/** Click: index finger bent / shorter */
const CLICK = [
  '..............',
  '..............',
  '......##......',
  '.....#oo#.....',
  '.....#oo#.....',
  '.....#oo#####.',
  '....#oo#ooo#.#',
  '...#oo#oooo#.#',
  '..#oo#ooooo#.#',
  '.#oo#oooooo#.#',
  '#oo#ooooooo##.',
  '#oo#oooooo#...',
  '.#o#oooooo#...',
  '..##o#ooo#....',
  '....#o#o#.....',
  '.....#o#......',
  '......#.......',
  '..............',
  '..............',
]

function spriteToDataUrl(rows: string[], scale = SCALE): string {
  const w = rows[0].length
  const h = rows.length
  const canvas = document.createElement('canvas')
  canvas.width = w * scale
  canvas.height = h * scale
  const ctx = canvas.getContext('2d')!
  ctx.imageSmoothingEnabled = false
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const ch = rows[y][x]
      if (ch === '#') ctx.fillStyle = '#000000'
      else if (ch === 'o') ctx.fillStyle = '#ffffff'
      else continue
      ctx.fillRect(x * scale, y * scale, scale, scale)
    }
  }
  return canvas.toDataURL('image/png')
}

function TextBeamUrl(scale = SCALE): string {
  const rows = [
    '.####.',
    '#oooo#',
    '#oooo#',
    '#oooo#',
    '#oooo#',
    '#oooo#',
    '#oooo#',
    '#oooo#',
    '#oooo#',
    '.####.',
  ]
  return spriteToDataUrl(rows, scale)
}

/**
 * Pointing-hand cursor that actually looks like a hand.
 * Canvas sprites (crisp pixels), smooth trail, click bends the finger.
 */
export function PixelCursor() {
  const rootRef = useRef<HTMLDivElement>(null)
  const mainRef = useRef<HTMLDivElement>(null)
  const trailRefs = useRef<(HTMLImageElement | null)[]>([])
  const openImg = useRef<HTMLImageElement>(null)
  const clickImg = useRef<HTMLImageElement>(null)
  const textImg = useRef<HTMLImageElement>(null)
  const urls = useRef<{ open: string; click: string; text: string } | null>(null)

  useEffect(() => {
    const fine = window.matchMedia('(pointer: fine)').matches
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const coarseTouch = window.matchMedia('(pointer: coarse)').matches
    if (!fine || reduce || coarseTouch) return

    const root = rootRef.current
    const main = mainRef.current
    if (!root || !main) return

    urls.current = {
      open: spriteToDataUrl(OPEN),
      click: spriteToDataUrl(CLICK),
      text: TextBeamUrl(),
    }

    const applySrc = () => {
      const u = urls.current!
      if (openImg.current) openImg.current.src = u.open
      if (clickImg.current) clickImg.current.src = u.click
      if (textImg.current) textImg.current.src = u.text
      for (const el of trailRefs.current) {
        if (el) el.src = u.open
      }
    }
    applySrc()

    document.documentElement.classList.add('pixel-cursor-on')
    root.style.opacity = '0'

    const mouse = { x: window.innerWidth / 2, y: window.innerHeight / 2, visible: false, down: false }
    const cursor = { x: mouse.x, y: mouse.y }
    const trails = Array.from({ length: TRAIL_LEN }, () => ({ x: mouse.x, y: mouse.y }))
    let raf = 0

    const setFrames = (mode: CursorMode, down: boolean) => {
      const text = mode === 'text'
      const clicking = !text && down
      if (openImg.current) openImg.current.style.opacity = text || clicking ? '0' : '1'
      if (clickImg.current) clickImg.current.style.opacity = clicking ? '1' : '0'
      if (textImg.current) textImg.current.style.opacity = text ? '1' : '0'
    }

    const onMove = (e: MouseEvent) => {
      mouse.x = e.clientX
      mouse.y = e.clientY
      if (!mouse.visible) {
        mouse.visible = true
        cursor.x = e.clientX
        cursor.y = e.clientY
        for (const t of trails) {
          t.x = e.clientX
          t.y = e.clientY
        }
        root.style.opacity = '1'
      }
      setFrames(resolveMode(e.target), mouse.down)
    }

    const onOver = (e: MouseEvent) => setFrames(resolveMode(e.target), mouse.down)
    const onDown = (e: MouseEvent) => {
      if (e.button !== 0) return
      mouse.down = true
      setFrames(resolveMode(e.target), true)
    }
    const onUp = (e?: Event) => {
      mouse.down = false
      const target = e && 'target' in e ? (e.target as EventTarget) : null
      setFrames(resolveMode(target), false)
    }
    const onLeave = () => {
      mouse.visible = false
      mouse.down = false
      root.style.opacity = '0'
      setFrames('default', false)
    }
    const onEnter = () => {
      mouse.visible = true
      root.style.opacity = '1'
    }

    const tick = () => {
      cursor.x += (mouse.x - cursor.x) * LERP
      cursor.y += (mouse.y - cursor.y) * LERP
      // Hotspot on fingertip
      main.style.transform = `translate3d(${cursor.x - 7}px, ${cursor.y - 2}px, 0)`

      let px = cursor.x
      let py = cursor.y
      for (let i = 0; i < TRAIL_LEN; i++) {
        const t = trails[i]
        t.x += (px - t.x) * (TRAIL_LERP * (1 - i * 0.06))
        t.y += (py - t.y) * (TRAIL_LERP * (1 - i * 0.06))
        px = t.x
        py = t.y
        const el = trailRefs.current[i]
        if (!el) continue
        const life = 1 - (i + 1) / (TRAIL_LEN + 1)
        el.style.transform = `translate3d(${t.x - 7}px, ${t.y - 2}px, 0)`
        el.style.opacity = String(life * 0.4)
      }

      raf = requestAnimationFrame(tick)
    }

    window.addEventListener('mousemove', onMove, { passive: true })
    window.addEventListener('mouseover', onOver, { passive: true })
    window.addEventListener('mousedown', onDown)
    window.addEventListener('mouseup', onUp)
    window.addEventListener('blur', onUp)
    document.documentElement.addEventListener('mouseleave', onLeave)
    document.documentElement.addEventListener('mouseenter', onEnter)
    raf = requestAnimationFrame(tick)
    setFrames('default', false)

    return () => {
      document.documentElement.classList.remove('pixel-cursor-on')
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseover', onOver)
      window.removeEventListener('mousedown', onDown)
      window.removeEventListener('mouseup', onUp)
      window.removeEventListener('blur', onUp)
      document.documentElement.removeEventListener('mouseleave', onLeave)
      document.documentElement.removeEventListener('mouseenter', onEnter)
      cancelAnimationFrame(raf)
    }
  }, [])

  const imgStyle: CSSProperties = {
    position: 'absolute',
    top: 0,
    left: 0,
    imageRendering: 'pixelated',
    pointerEvents: 'none',
    userSelect: 'none',
  }

  return (
    <div ref={rootRef} className="pointer-events-none fixed inset-0 z-[9999] transition-opacity duration-100" aria-hidden>
      {Array.from({ length: TRAIL_LEN }).map((_, i) => (
        <img
          key={i}
          ref={el => {
            trailRefs.current[i] = el
          }}
          alt=""
          draggable={false}
          className="absolute top-0 left-0 will-change-transform"
          style={{ ...imgStyle, position: 'absolute', opacity: 0, imageRendering: 'pixelated' }}
        />
      ))}

      <div ref={mainRef} className="absolute top-0 left-0 will-change-transform" style={{ width: 14 * SCALE, height: 19 * SCALE }}>
        <img ref={openImg} alt="" draggable={false} style={{ ...imgStyle, opacity: 1 }} />
        <img ref={clickImg} alt="" draggable={false} style={{ ...imgStyle, opacity: 0 }} />
        <img ref={textImg} alt="" draggable={false} style={{ ...imgStyle, opacity: 0, left: 4 }} />
      </div>
    </div>
  )
}
