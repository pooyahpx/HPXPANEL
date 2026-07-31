import * as React from 'react'

import { cn } from '@/lib/utils'

const Textarea = React.forwardRef<HTMLTextAreaElement, React.ComponentProps<'textarea'>>(({ className, ...props }, ref) => {
  return (
    <textarea
      className={cn(
        'bg-input placeholder:text-input-placeholder focus-visible:border-primary flex min-h-24 w-full rounded-none border-2 border-[hsl(var(--pixel-border))] px-3.5 py-3 text-base leading-5 shadow-[3px_3px_0_0_hsl(var(--pixel-border))] transition-[box-shadow,transform,border-color] focus-visible:translate-x-[2px] focus-visible:translate-y-[2px] focus-visible:shadow-none focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none md:text-sm',
        className,
      )}
      ref={ref}
      {...props}
    />
  )
})
Textarea.displayName = 'Textarea'

export { Textarea }
