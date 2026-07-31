import * as React from 'react'
import * as PopoverPrimitive from '@radix-ui/react-popover'

import { cn } from '@/lib/utils'

const Popover = PopoverPrimitive.Root

const PopoverTrigger = PopoverPrimitive.Trigger

const PopoverAnchor = PopoverPrimitive.Anchor

const PopoverContent = React.forwardRef<React.ElementRef<typeof PopoverPrimitive.Content>, React.ComponentPropsWithoutRef<typeof PopoverPrimitive.Content> & { disablePortal?: boolean }>(
  ({ className, align = 'center', sideOffset = 4, collisionPadding = 8, disablePortal = false, ...props }, ref) => {
    const content = (
      <PopoverPrimitive.Content
        ref={ref}
        align={align}
        sideOffset={sideOffset}
        collisionPadding={collisionPadding}
        className={cn(
          'bg-popover text-popover-foreground data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[side=bottom]:slide-in-from-top-1 data-[side=left]:slide-in-from-right-1 data-[side=right]:slide-in-from-left-1 data-[side=top]:slide-in-from-bottom-1 z-60 w-72 max-w-[calc(100vw-1rem)] origin-(--radix-popover-content-transform-origin) rounded-none border-2 border-[hsl(var(--pixel-border))] p-4 text-xs shadow-[4px_4px_0_0_hsl(var(--pixel-border))] outline-none motion-reduce:animate-none',
          className,
        )}
        {...props}
      />
    )
    return disablePortal ? content : <PopoverPrimitive.Portal>{content}</PopoverPrimitive.Portal>
  },
)
PopoverContent.displayName = PopoverPrimitive.Content.displayName

export { Popover, PopoverTrigger, PopoverContent, PopoverAnchor }
