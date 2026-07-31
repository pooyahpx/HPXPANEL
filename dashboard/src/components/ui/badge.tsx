import { cva, type VariantProps } from 'class-variance-authority'
import * as React from 'react'

import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center rounded-none border-2 border-[hsl(var(--pixel-border))] px-2 py-0.5 font-body text-xs font-semibold tracking-[0.02em] uppercase transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground shadow-[2px_2px_0_0_hsl(var(--pixel-border))]',
        secondary: 'bg-secondary text-secondary-foreground shadow-[2px_2px_0_0_hsl(var(--pixel-border))]',
        destructive: 'bg-destructive text-destructive-foreground shadow-[2px_2px_0_0_hsl(var(--pixel-border))]',
        outline: 'text-foreground bg-background shadow-[2px_2px_0_0_hsl(var(--pixel-border))]',
        green: 'bg-emerald-400/30 text-emerald-900 shadow-[2px_2px_0_0_hsl(var(--pixel-border))] dark:text-emerald-200',
        red: 'bg-rose-400/30 text-rose-900 shadow-[2px_2px_0_0_hsl(var(--pixel-border))] dark:text-rose-200',
        yellow: 'bg-amber-400/30 text-amber-950 shadow-[2px_2px_0_0_hsl(var(--pixel-border))] dark:text-amber-200',
        blue: 'bg-sky-400/30 text-sky-950 shadow-[2px_2px_0_0_hsl(var(--pixel-border))] dark:text-sky-200',
        orange: 'bg-orange-400/30 text-orange-950 shadow-[2px_2px_0_0_hsl(var(--pixel-border))] dark:text-orange-200',
        blank: 'bg-muted text-muted-foreground shadow-[2px_2px_0_0_hsl(var(--pixel-border))]',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
)

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge, badgeVariants }
