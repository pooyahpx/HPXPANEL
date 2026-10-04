import { cn } from '@/lib/utils'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import { LoaderCircleIcon } from 'lucide-react'
import * as React from 'react'

const buttonVariants = cva(
  [
    'inline-flex cursor-pointer items-center justify-center gap-2 whitespace-nowrap',
    'font-body font-semibold tracking-normal leading-none',
    'rounded-xl border border-transparent',
    'ring-offset-background select-none',
    'transition-[transform,box-shadow,background-color,border-color] duration-200 ease-out',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/60 focus-visible:ring-offset-2',
    'disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50',
    'active:scale-[0.98]',
  ].join(' '),
  {
    variants: {
      variant: {
        default: [
          'bg-primary text-primary-foreground shadow-lg shadow-primary/25',
          'hover:bg-[hsl(var(--hover-primary))] hover:shadow-primary/35',
        ].join(' '),
        destructive: [
          'bg-destructive text-destructive-foreground shadow-lg shadow-destructive/20',
          'hover:bg-[hsl(var(--hover-destructive))]',
        ].join(' '),
        outline: [
          'bg-background/60 text-foreground border-border/80 backdrop-blur-sm',
          'hover:bg-secondary/80 hover:border-primary/30',
        ].join(' '),
        secondary: [
          'bg-secondary/90 text-secondary-foreground',
          'hover:bg-[hsl(var(--hover-secondary))]',
        ].join(' '),
        ghost: [
          'hover:bg-accent/80 hover:text-accent-foreground',
          'active:scale-100',
        ].join(' '),
        link: ['border-transparent text-primary underline-offset-4', 'hover:underline', 'active:scale-100'].join(' '),
      },
      size: {
        default: 'h-10 px-4 py-2 text-sm',
        sm: 'h-9 px-3 text-sm [&>svg]:w-4 [&>svg]:h-4',
        lg: 'h-12 px-6 text-base gap-3',
        icon: 'h-8 w-8 p-0 [&>svg]:w-4 [&>svg]:h-4 [&>svg]:stroke-[1.5px]',
        'icon-md': 'h-9 w-9 p-0 [&>svg]:w-4 [&>svg]:h-4 [&>svg]:stroke-[1.5px]',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
)

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean
  isLoading?: boolean
  loadingText?: string
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, isLoading = false, loadingText, children, ...rest }, ref) => {
    const Comp = isLoading ? 'button' : asChild ? Slot : 'button'
    const content = isLoading ? (
      <>
        <LoaderCircleIcon className="h-5 w-5 animate-spin" />
        {loadingText}
      </>
    ) : (
      children
    )
    return (
      <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} disabled={isLoading || rest.disabled} {...rest}>
        {content}
      </Comp>
    )
  },
)
Button.displayName = 'Button'

export { Button, buttonVariants }
