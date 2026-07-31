import { cn } from '@/lib/utils'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import { LoaderCircleIcon } from 'lucide-react'
import * as React from 'react'

const buttonVariants = cva(
  [
    'inline-flex cursor-pointer items-center justify-center gap-2 whitespace-nowrap',
    'font-body font-semibold tracking-normal leading-none',
    'rounded-none border-2 border-[hsl(var(--pixel-border))]',
    'ring-offset-background select-none',
    'transition-[transform,box-shadow,background-color] duration-[90ms] ease-out',
    'focus-visible:outline-none',
    'disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none disabled:translate-x-0 disabled:translate-y-0',
    'active:translate-x-[4px] active:translate-y-[4px] active:shadow-none',
    'motion-reduce:active:translate-x-[2px] motion-reduce:active:translate-y-[2px]',
  ].join(' '),
  {
    variants: {
      variant: {
        default: [
          'bg-primary text-primary-foreground',
          'shadow-[4px_4px_0_0_hsl(var(--pixel-border))]',
          'hover:bg-[hsl(var(--hover-primary))]',
          'focus-visible:shadow-[4px_4px_0_0_hsl(var(--pixel-border)),0_0_0_2px_hsl(var(--destructive)/0.65)]',
        ].join(' '),
        destructive: [
          'bg-destructive text-destructive-foreground',
          'shadow-[4px_4px_0_0_hsl(var(--pixel-border))]',
          'hover:bg-[hsl(var(--hover-destructive))]',
          'focus-visible:shadow-[4px_4px_0_0_hsl(var(--pixel-border)),0_0_0_2px_hsl(var(--primary)/0.65)]',
        ].join(' '),
        outline: [
          'bg-background text-foreground',
          'shadow-[4px_4px_0_0_hsl(var(--pixel-border))]',
          'hover:bg-secondary',
          'focus-visible:shadow-[4px_4px_0_0_hsl(var(--pixel-border)),0_0_0_2px_hsl(var(--primary)/0.65)]',
        ].join(' '),
        secondary: [
          'bg-secondary text-secondary-foreground',
          'shadow-[4px_4px_0_0_hsl(var(--pixel-border))]',
          'hover:bg-[hsl(var(--hover-secondary))]',
          'focus-visible:shadow-[4px_4px_0_0_hsl(var(--pixel-border)),0_0_0_2px_hsl(var(--primary)/0.65)]',
        ].join(' '),
        ghost: [
          'border-transparent shadow-none',
          'hover:bg-accent hover:text-accent-foreground hover:border-[hsl(var(--pixel-border))]',
          'active:translate-x-0 active:translate-y-0',
          'focus-visible:border-[hsl(var(--pixel-border))] focus-visible:ring-2 focus-visible:ring-ring',
        ].join(' '),
        link: ['border-transparent shadow-none text-primary underline-offset-4', 'hover:underline', 'active:translate-x-0 active:translate-y-0', 'focus-visible:ring-2 focus-visible:ring-ring'].join(
          ' ',
        ),
      },
      size: {
        default: 'h-10 px-4 py-2 text-sm',
        sm: 'h-9 px-3 text-sm [&>svg]:w-4 [&>svg]:h-4',
        lg: 'h-12 px-6 text-base gap-3',
        icon: 'h-8 w-8 p-0 [&>svg]:w-4 [&>svg]:h-4 [&>svg]:stroke-[1.5px] shadow-[3px_3px_0_0_hsl(var(--pixel-border))] active:translate-x-[3px] active:translate-y-[3px]',
        'icon-md': 'h-9 w-9 p-0 [&>svg]:w-4 [&>svg]:h-4 [&>svg]:stroke-[1.5px] shadow-[3px_3px_0_0_hsl(var(--pixel-border))] active:translate-x-[3px] active:translate-y-[3px]',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
    compoundVariants: [
      {
        variant: 'ghost',
        size: ['icon', 'icon-md'],
        class: 'shadow-none active:translate-x-0 active:translate-y-0',
      },
      {
        variant: 'link',
        size: ['icon', 'icon-md'],
        class: 'shadow-none active:translate-x-0 active:translate-y-0',
      },
    ],
  },
)

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean
  isLoading?: boolean
  loadingText?: string
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(({ className, variant, size, asChild = false, isLoading = false, loadingText, children, ...rest }, ref) => {
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
    <Comp className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...rest}>
      {content}
    </Comp>
  )
})
Button.displayName = 'Button'

export { Button, buttonVariants }
