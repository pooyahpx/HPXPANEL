import * as React from 'react'
import { cn } from '@/lib/utils'

export interface HpxRecLoaderProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Accent color (dot / laptop / HPX text). Default: deep blue. */
  accentColor?: string
  /** Fill used in the mid animation beats. Default: near-black navy. */
  inkColor?: string
  /** Brand label shown instead of REC. */
  label?: string
}

/**
 * HPX record → laptop morph loader (no styled-components).
 * Scoped CSS via React.useId so multiple instances don't clash.
 */
const HpxRecLoader = React.forwardRef<HTMLDivElement, HpxRecLoaderProps>(
  ({ className, accentColor = '#2563eb', inkColor = '#020617', label = 'HPX', ...props }, ref) => {
    const reactId = React.useId().replace(/:/g, '')
    const root = `hpx-rec-${reactId}`

    const style = {
      '--hpx-rec-accent': accentColor,
      '--hpx-rec-ink': inkColor,
    } as React.CSSProperties

    return (
      <div
        ref={ref}
        className={cn('relative flex h-[12em] w-[14em] items-center justify-center text-[10px] sm:text-[11px]', className)}
        style={style}
        role="status"
        aria-label="Loading"
        {...props}
      >
        <style>
          {`
            .${root} {
              --c: var(--hpx-rec-accent);
              --ink: var(--hpx-rec-ink);
              position: relative;
              width: 100%;
              height: 100%;
            }

            .${root} .ph1 {
              position: absolute;
              left: 50%;
              top: 50%;
              transform: translate(-50%, -50%);
              display: flex;
              flex-direction: row;
              align-items: center;
              gap: 8px;
              animation: ${root}-ph1 3s ease infinite;
              clip-path: polygon(-4em -1em, 4em -1em, 4em 1em, -4em 1em);
            }

            .${root} .record {
              position: absolute;
              left: 50%;
              top: 50%;
              width: 2em;
              height: 2em;
              background: var(--c);
              border-radius: 999px;
              animation: ${root}-blink 1s step-end infinite;
              transform: translate(-3.5em, -50%);
            }

            .${root} .record-text {
              position: absolute;
              color: var(--c);
              font-size: 2.2em;
              font-weight: 700;
              letter-spacing: 0.06em;
              left: 50%;
              top: 50%;
              transform: translate(-0.5em, -50%);
              width: 2.4em;
              height: 1.5em;
              line-height: 1.5em;
            }

            @keyframes ${root}-blink {
              50% { opacity: 0; }
              75% { opacity: 1; }
            }

            @keyframes ${root}-ph1 {
              25.5% {
                translate: 0 0;
                clip-path: polygon(-4em -1em, 4em -1em, 4em 1em, -4em 1em);
              }
              30%, to {
                opacity: 1;
                translate: 0 3em;
                clip-path: polygon(-4em 1em, 4em 1em, 4em 1em, -4em 1em);
              }
              30.1% {
                opacity: 0;
                translate: 0 3em;
              }
              92.4%, to {
                translate: 0 0;
                opacity: 0;
                clip-path: polygon(-4em -1em, 4em -1em, 4em 1em, -4em 1em);
              }
              92.5% {
                opacity: 1;
                clip-path: polygon(-4em -1em, -0.5em -1em, -0.5em 1em, -4em 1em);
              }
              to {
                opacity: 1;
                clip-path: polygon(-4em -1em, 4em -1em, 4em 1em, -4em 1em);
              }
            }

            .${root} .ph2 {
              position: absolute;
              left: 50%;
              top: 50%;
              transform: translate(-50%, -4em);
              width: 11em;
              height: 7em;
              perspective: 150px;
              perspective-origin: 50% 0%;
              transform-style: preserve-3d;
              animation: ${root}-ph2 3s ease-in-out infinite;
            }

            @keyframes ${root}-ph2 {
              0%, 15% { translate: 0 4em; }
              0%, 29% { opacity: 0; }
              30% { opacity: 1; }
              40% { translate: 0 0; }
              50% {
                translate: 0 0.5em;
                opacity: 1;
              }
              50.1%, to { opacity: 0; }
            }

            .${root} .laptop-b {
              position: absolute;
              left: 0;
              right: 0;
              bottom: 0;
              height: 0.5em;
              background: var(--c);
              border-bottom-left-radius: 2em;
              border-bottom-right-radius: 2em;
              animation: ${root}-ph2b 3s ease infinite;
            }

            .${root} .laptop-t {
              margin: 0 1.25em;
              color: var(--c);
              transform-origin: 50% 100%;
              animation: ${root}-ph2t 3s ease infinite;
            }

            @keyframes ${root}-ph2t {
              0%, 29% { transform: rotateX(-10deg); }
              0%, 41.9% { stroke-dasharray: unset; }
              42% {
                transform: rotateX(4deg);
                stroke-dasharray: 0 0 100;
              }
              50% {
                transform: rotateX(-20deg);
                stroke-dasharray: 0 50 0 100;
              }
            }

            @keyframes ${root}-ph2b {
              42% { scale: 1 1; }
              50% { scale: 0 1; }
            }

            .${root} .icon {
              position: absolute;
              width: 4em;
              height: 4em;
              background: var(--c);
              border-radius: 999px;
              top: 50%;
              left: 50%;
              transform: translate(-50%, -50%);
              transform-origin: center;
              animation: ${root}-icon 3s ease-in-out infinite;
              isolation: isolate;
              border-color: var(--c);
              border-style: solid;
              z-index: -1;
            }

            @keyframes ${root}-icon {
              0%, 15% {
                translate: 0 4.5em;
                width: 0;
                height: 0;
              }
              0%, 29% { opacity: 0; }
              30% { opacity: 1; }
              40% {
                translate: 0 -0.75em;
                width: 4em;
                height: 4em;
              }
              50% {
                translate: 0 0em;
                opacity: 1;
                background: var(--c);
              }
              50.1% {
                border-width: 2em;
                background: var(--ink);
              }
              65% {
                width: 4em;
                height: 4em;
                transform: translate(-50%, -50%);
                border-width: 4px;
              }
              80%, to {
                width: 2em;
                height: 2em;
                translate: 0 0;
                transform: translate(-3.5em, -50%);
                border-width: 1em;
                background: var(--ink);
              }
              80.1%, to { background: var(--c); }
              84.9% { opacity: 1; }
              85%, to { opacity: 0; }
            }

            .${root} .icon::before {
              content: "";
              position: absolute;
              top: 50%;
              left: 50%;
              border: 0.8em solid var(--ink);
              box-sizing: border-box;
              border-left-color: transparent !important;
              border-bottom-color: transparent !important;
              transform: translate(-50%, 2.5em) rotate(-45deg);
              transform-origin: center;
              animation: ${root}-iconb 3s ease-in-out infinite;
              z-index: -1;
            }

            @keyframes ${root}-iconb {
              20% { transform: translate(-50%, 2.5em) rotate(-45deg); }
              50% {
                transform: translate(-50%, -25%) rotate(-45deg);
                border-color: var(--ink);
              }
              65%, to {
                transform: translateY(0) scale(1) scaleX(1.5) translate(-60%, -50%) rotate(45deg);
                border-color: var(--c);
              }
              85%, to {
                transform: translate(-40%, -50%) scale(0) scaleX(1.5) translate(-75%, -50%) rotate(45deg);
              }
            }

            .${root} .icon::after {
              content: "";
              position: absolute;
              top: 50%;
              left: 50%;
              background: var(--ink);
              width: 1em;
              height: 2em;
              box-sizing: border-box;
              border-left-color: transparent;
              border-bottom-color: transparent;
              animation: ${root}-icona 3s ease-in-out infinite;
            }

            @keyframes ${root}-icona {
              20% { transform: translate(-50%, 2.5em); }
              50% { transform: translate(-50%, 0.4em); }
              65%, to { transform: translate(-50%, 2.5em); }
            }

            @media (prefers-reduced-motion: reduce) {
              .${root} .ph1,
              .${root} .ph2,
              .${root} .laptop-b,
              .${root} .laptop-t,
              .${root} .record,
              .${root} .icon,
              .${root} .icon::before,
              .${root} .icon::after {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
              }
            }
          `}
        </style>

        <div className={root}>
          <div className="ph1">
            <div className="record" />
            <div className="record-text">{label}</div>
          </div>
          <div className="ph2">
            <div className="laptop-b" />
            <svg className="laptop-t" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 42 30" aria-hidden="true">
              <path
                d="M21 1H5C2.78 1 1 2.78 1 5V25a4 4 90 004 4H37a4 4 90 004-4V5c0-2.22-1.8-4-4-4H21"
                pathLength={100}
                strokeWidth={2}
                stroke="currentColor"
                fill="none"
              />
            </svg>
          </div>
          <div className="icon" />
        </div>
      </div>
    )
  },
)
HpxRecLoader.displayName = 'HpxRecLoader'

export { HpxRecLoader }
export default HpxRecLoader
