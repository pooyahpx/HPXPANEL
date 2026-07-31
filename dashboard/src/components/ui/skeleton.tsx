import { cn } from '@/lib/utils'

function Skeleton({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      data-slot="skeleton"
      aria-hidden="true"
      className={cn(
        'bg-muted/70 relative overflow-hidden rounded-none border border-[hsl(var(--pixel-border)/0.35)]',
        'before:animate-skeleton-shimmer before:absolute before:inset-0 before:-translate-x-full',
        'before:via-primary/15 before:bg-gradient-to-r before:from-transparent before:to-transparent',
        'motion-reduce:before:animate-none',
        className,
      )}
      {...props}
    />
  )
}

export { Skeleton }
