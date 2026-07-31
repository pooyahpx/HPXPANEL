import * as React from 'react'
import * as TabsPrimitive from '@radix-ui/react-tabs'

import { cn } from '@/lib/utils'

const Tabs = TabsPrimitive.Root

const TabsList = React.forwardRef<React.ElementRef<typeof TabsPrimitive.List>, React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>>(({ className, ...props }, ref) => (
  <TabsPrimitive.List
    ref={ref}
    className={cn('bg-muted/60 text-muted-foreground inline-flex min-h-11 items-center justify-center rounded-none border-2 border-[hsl(var(--pixel-border))] p-1', className)}
    {...props}
  />
))
TabsList.displayName = TabsPrimitive.List.displayName

const TabsTrigger = React.forwardRef<React.ElementRef<typeof TabsPrimitive.Trigger>, React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>>(({ className, ...props }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(
      'text-muted-foreground data-[state=active]:bg-primary data-[state=active]:text-primary-foreground focus-visible:border-primary focus-visible:ring-ring inline-flex min-h-9 items-center justify-center rounded-none border-2 border-transparent px-3 py-1.5 font-mono text-xs font-bold tracking-wide whitespace-nowrap uppercase transition-[color,background-color,border-color] focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50 data-[state=active]:border-[hsl(var(--pixel-border))] motion-reduce:transition-none',
      className,
    )}
    {...props}
  />
))
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName

const TabsContent = React.forwardRef<React.ElementRef<typeof TabsPrimitive.Content>, React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>>(({ className, ...props }, ref) => (
  <TabsPrimitive.Content ref={ref} className={cn('focus-visible:ring-ring mt-3 rounded-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none', className)} {...props} />
))
TabsContent.displayName = TabsPrimitive.Content.displayName

export { Tabs, TabsList, TabsTrigger, TabsContent }
