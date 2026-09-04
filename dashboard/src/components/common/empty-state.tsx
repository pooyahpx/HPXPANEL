import { Card, CardContent } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

export interface EmptyStateProps {
  icon?: LucideIcon
  title: string
  description?: ReactNode
  action?: ReactNode
  className?: string
}

export function EmptyState({ icon: Icon, title, description, action, className }: EmptyStateProps) {
  return (
    <Card className={cn('mb-12', className)}>
      <CardContent className="flex flex-col items-center justify-center gap-3 px-6 py-8 text-center">
        {Icon ? (
          <div className="bg-muted/40 text-muted-foreground flex h-10 w-10 items-center justify-center border">
            <Icon className="h-5 w-5" aria-hidden="true" />
          </div>
        ) : null}
        <div className="space-y-1.5">
          <h3 className="text-base font-semibold">{title}</h3>
          {description ? <div className="text-muted-foreground mx-auto max-w-md text-sm leading-relaxed">{description}</div> : null}
        </div>
        {action ? <div className="pt-1">{action}</div> : null}
      </CardContent>
    </Card>
  )
}
