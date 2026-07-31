import * as React from 'react'
import * as SwitchPrimitives from '@radix-ui/react-switch'

import { cn } from '@/lib/utils'

const Switch = React.forwardRef<React.ElementRef<typeof SwitchPrimitives.Root>, React.ComponentPropsWithoutRef<typeof SwitchPrimitives.Root>>(({ className, ...props }, ref) => (
  <SwitchPrimitives.Root
    className={cn(
      'peer data-[state=checked]:bg-primary data-[state=unchecked]:bg-input focus-visible:border-primary focus-visible:ring-ring inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-none border-2 border-[hsl(var(--pixel-border))] shadow-[2px_2px_0_0_hsl(var(--pixel-border))] transition-[background-color,box-shadow,border-color] focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none',
      className,
    )}
    {...props}
    ref={ref}
    dir="ltr"
  >
    <SwitchPrimitives.Thumb
      className={cn(
        'bg-foreground data-[state=checked]:bg-primary-foreground pointer-events-none block h-4 w-4 rounded-none border border-[hsl(var(--pixel-border))] ring-0 transition-transform data-[state=checked]:translate-x-5 data-[state=unchecked]:translate-x-0 motion-reduce:transition-none',
      )}
    />
  </SwitchPrimitives.Root>
))
Switch.displayName = SwitchPrimitives.Root.displayName

export { Switch }
