import * as React from 'react'
import { cn } from '@/lib/utils'

export interface GooeyLoaderProps extends React.HTMLAttributes<HTMLDivElement> {
  /** The primary color for the goo effect. Defaults to shadcn's primary color. */
  primaryColor?: string
  /** The secondary color for the goo effect. Defaults to shadcn's secondary color. */
  secondaryColor?: string
  /** The color for the bottom border. Defaults to shadcn's border color. */
  borderColor?: string
}

const GooeyLoader = React.forwardRef<HTMLDivElement, GooeyLoaderProps>(
  ({ className, primaryColor, secondaryColor, borderColor, ...props }, ref) => {
    const reactId = React.useId().replace(/:/g, '')
    const filterId = `gooey-loader-filter-${reactId}`

    const style = {
      '--gooey-primary-color': primaryColor || 'hsl(var(--primary))',
      '--gooey-secondary-color': secondaryColor || 'hsl(var(--secondary))',
      '--gooey-border-color': borderColor || 'hsl(var(--border))',
    } as React.CSSProperties

    return (
      <div
        ref={ref}
        className={cn('relative flex items-center justify-center text-sm', className)}
        style={style}
        role="status"
        aria-label="Loading"
        {...props}
      >
        <svg className="absolute h-0 w-0" aria-hidden="true">
          <defs>
            <filter id={filterId}>
              <feGaussianBlur in="SourceGraphic" stdDeviation={12} result="blur" />
              <feColorMatrix
                in="blur"
                mode="matrix"
                values="1 0 0 0 0  0 1 0 0 0  0 0 1 0 0  0 0 0 48 -7"
                result="goo"
              />
              <feComposite in="SourceGraphic" in2="goo" operator="atop" />
            </filter>
          </defs>
        </svg>

        <style>
          {`
            .gooey-loader-${reactId} {
              width: 12em;
              height: 3em;
              position: relative;
              overflow: hidden;
              border-bottom: 8px solid var(--gooey-border-color);
              filter: url(#${filterId});
            }

            .gooey-loader-${reactId}::before,
            .gooey-loader-${reactId}::after {
              content: '';
              position: absolute;
              border-radius: 50%;
            }

            .gooey-loader-${reactId}::before {
              width: 22em;
              height: 18em;
              background-color: var(--gooey-primary-color);
              left: -2em;
              bottom: -18em;
              animation: gooey-loader-wee1-${reactId} 2s linear infinite;
            }

            .gooey-loader-${reactId}::after {
              width: 16em;
              height: 12em;
              background-color: var(--gooey-secondary-color);
              left: -4em;
              bottom: -12em;
              animation: gooey-loader-wee2-${reactId} 2s linear infinite 0.75s;
            }

            @keyframes gooey-loader-wee1-${reactId} {
              0% { transform: translateX(-10em) rotate(0deg); }
              100% { transform: translateX(7em) rotate(180deg); }
            }

            @keyframes gooey-loader-wee2-${reactId} {
              0% { transform: translateX(-8em) rotate(0deg); }
              100% { transform: translateX(8em) rotate(180deg); }
            }

            @media (prefers-reduced-motion: reduce) {
              .gooey-loader-${reactId}::before,
              .gooey-loader-${reactId}::after {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
              }
            }
          `}
        </style>

        <div className={`gooey-loader-${reactId}`} />
      </div>
    )
  },
)
GooeyLoader.displayName = 'GooeyLoader'

export { GooeyLoader }
