import { cn } from '@/lib/utils'
import * as React from 'react'

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  error?: string
  isError?: boolean
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(({ className, type, error, isError, ...props }, ref) => {
  return (
    <div className="min-w-0 flex-1">
      <input
        type={type}
        dir="ltr"
        className={cn(
          'bg-input ring-offset-background file:text-foreground placeholder:text-input-placeholder focus-visible:border-primary font-body flex h-11 w-full rounded-none border-2 border-[hsl(var(--pixel-border))] px-3.5 py-2 text-sm leading-5 shadow-[3px_3px_0_0_hsl(var(--pixel-border))] transition-[box-shadow,transform,border-color] file:border-0 file:bg-transparent file:text-sm file:font-medium focus-visible:translate-x-[2px] focus-visible:translate-y-[2px] focus-visible:shadow-none focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50',
          className,
          {
            'border-destructive': !!error || isError,
          },
        )}
        ref={ref}
        {...props}
      />
      {error && <span className="text-destructive mt-2 block text-sm">{error}</span>}
    </div>
  )
})
Input.displayName = 'Input'

export { Input }
