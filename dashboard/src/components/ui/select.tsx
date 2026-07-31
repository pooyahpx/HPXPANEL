import * as SelectPrimitive from '@radix-ui/react-select'
import { Check, ChevronDown, ChevronUp } from 'lucide-react'
import * as React from 'react'

import { cn } from '@/lib/utils'

const Select = SelectPrimitive.Root

const SelectGroup = SelectPrimitive.Group

const SelectValue = SelectPrimitive.Value

const SelectTrigger = React.forwardRef<React.ElementRef<typeof SelectPrimitive.Trigger>, React.ComponentPropsWithoutRef<typeof SelectPrimitive.Trigger> & { icon?: boolean }>(
  ({ className, children, icon = true, ...props }, ref) => (
    <SelectPrimitive.Trigger
      ref={ref}
      className={cn(
        'bg-input placeholder:text-muted-foreground focus:border-primary flex h-11 w-full items-center justify-between rounded-none border-2 border-[hsl(var(--pixel-border))] px-3.5 py-2 text-sm whitespace-nowrap shadow-[3px_3px_0_0_hsl(var(--pixel-border))] transition-[box-shadow,transform,border-color] focus:translate-x-[2px] focus:translate-y-[2px] focus:shadow-none focus:outline-none disabled:cursor-not-allowed disabled:opacity-50 motion-reduce:transition-none [&>span]:line-clamp-1',
        className,
      )}
      {...props}
    >
      {children}
      {icon && (
        <SelectPrimitive.Icon asChild>
          <ChevronDown className="h-4 w-4 opacity-70" />
        </SelectPrimitive.Icon>
      )}
    </SelectPrimitive.Trigger>
  ),
)
SelectTrigger.displayName = SelectPrimitive.Trigger.displayName

const SelectScrollUpButton = React.forwardRef<React.ElementRef<typeof SelectPrimitive.ScrollUpButton>, React.ComponentPropsWithoutRef<typeof SelectPrimitive.ScrollUpButton>>(
  ({ className, ...props }, ref) => (
    <SelectPrimitive.ScrollUpButton ref={ref} className={cn('flex h-9 cursor-default items-center justify-center border-b border-[hsl(var(--pixel-border))]', className)} {...props}>
      <ChevronUp className="h-4 w-4" />
    </SelectPrimitive.ScrollUpButton>
  ),
)
SelectScrollUpButton.displayName = SelectPrimitive.ScrollUpButton.displayName

const SelectScrollDownButton = React.forwardRef<React.ElementRef<typeof SelectPrimitive.ScrollDownButton>, React.ComponentPropsWithoutRef<typeof SelectPrimitive.ScrollDownButton>>(
  ({ className, ...props }, ref) => (
    <SelectPrimitive.ScrollDownButton ref={ref} className={cn('flex h-9 cursor-default items-center justify-center border-t border-[hsl(var(--pixel-border))]', className)} {...props}>
      <ChevronDown className="h-4 w-4" />
    </SelectPrimitive.ScrollDownButton>
  ),
)
SelectScrollDownButton.displayName = SelectPrimitive.ScrollDownButton.displayName

const SelectContent = React.forwardRef<React.ElementRef<typeof SelectPrimitive.Content>, React.ComponentPropsWithoutRef<typeof SelectPrimitive.Content>>(
  ({ className, children, position = 'popper', ...props }, ref) => (
    <SelectPrimitive.Portal>
      <SelectPrimitive.Content
        ref={ref}
        className={cn(
          'bg-popover text-popover-foreground data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 relative z-50 max-h-96 min-w-[5rem] overflow-hidden rounded-none border-2 border-[hsl(var(--pixel-border))] shadow-[4px_4px_0_0_hsl(var(--pixel-border))] motion-reduce:animate-none',
          position === 'popper' && 'data-[side=bottom]:translate-y-1 data-[side=left]:-translate-x-1 data-[side=right]:translate-x-1 data-[side=top]:-translate-y-1',
          className,
        )}
        position={position}
        {...props}
      >
        <SelectScrollUpButton />
        <SelectPrimitive.Viewport className={cn('p-1.5', position === 'popper' && 'h-[var(--radix-select-trigger-height)] w-full min-w-[var(--radix-select-trigger-width)]')}>
          {children}
        </SelectPrimitive.Viewport>
        <SelectScrollDownButton />
      </SelectPrimitive.Content>
    </SelectPrimitive.Portal>
  ),
)
SelectContent.displayName = SelectPrimitive.Content.displayName

const SelectLabel = React.forwardRef<React.ElementRef<typeof SelectPrimitive.Label>, React.ComponentPropsWithoutRef<typeof SelectPrimitive.Label>>(({ className, ...props }, ref) => (
  <SelectPrimitive.Label ref={ref} className={cn('text-muted-foreground px-2 py-2 font-mono text-[11px] font-bold tracking-[0.12em] uppercase', className)} {...props} />
))
SelectLabel.displayName = SelectPrimitive.Label.displayName

const SelectItem = React.forwardRef<React.ElementRef<typeof SelectPrimitive.Item>, React.ComponentPropsWithoutRef<typeof SelectPrimitive.Item>>(({ className, children, ...props }, ref) => (
  <SelectPrimitive.Item
    ref={ref}
    className={cn(
      'focus:bg-primary focus:text-primary-foreground relative flex min-h-11 w-full cursor-default items-center rounded-none border border-transparent py-2 ps-2.5 pe-9 text-sm outline-none select-none focus:border-[hsl(var(--pixel-border))] data-[disabled]:pointer-events-none data-[disabled]:opacity-50',
      className,
    )}
    {...props}
  >
    <span className="absolute end-2 flex h-3.5 w-3.5 items-center justify-center">
      <SelectPrimitive.ItemIndicator>
        <Check className="h-4 w-4" />
      </SelectPrimitive.ItemIndicator>
    </span>
    <SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>
  </SelectPrimitive.Item>
))
SelectItem.displayName = SelectPrimitive.Item.displayName

const SelectSeparator = React.forwardRef<React.ElementRef<typeof SelectPrimitive.Separator>, React.ComponentPropsWithoutRef<typeof SelectPrimitive.Separator>>(({ className, ...props }, ref) => (
  <SelectPrimitive.Separator ref={ref} className={cn('-mx-1.5 my-1.5 h-px bg-[hsl(var(--pixel-border))]', className)} {...props} />
))
SelectSeparator.displayName = SelectPrimitive.Separator.displayName

export { Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectScrollDownButton, SelectScrollUpButton, SelectSeparator, SelectTrigger, SelectValue }
