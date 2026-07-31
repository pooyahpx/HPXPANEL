import * as React from 'react'

import { cn } from '@/lib/utils'

const Table = React.forwardRef<HTMLTableElement, React.HTMLAttributes<HTMLTableElement>>(({ className, ...props }, ref) => (
  <div className="relative w-full overflow-auto rounded-none border-2 border-[hsl(var(--pixel-border))]">
    <table ref={ref} className={cn('w-full caption-bottom text-sm', className)} {...props} />
  </div>
))
Table.displayName = 'Table'

const TableHeader = React.forwardRef<HTMLTableSectionElement, React.HTMLAttributes<HTMLTableSectionElement>>(({ className, ...props }, ref) => (
  <thead ref={ref} className={cn('bg-muted/60 [&_tr]:border-b-2 [&_tr]:border-[hsl(var(--pixel-border))]', className)} {...props} />
))
TableHeader.displayName = 'TableHeader'

const TableBody = React.forwardRef<HTMLTableSectionElement, React.HTMLAttributes<HTMLTableSectionElement>>(({ className, ...props }, ref) => (
  <tbody ref={ref} className={cn('[&_tr:last-child]:border-0', className)} {...props} />
))
TableBody.displayName = 'TableBody'

const TableFooter = React.forwardRef<HTMLTableSectionElement, React.HTMLAttributes<HTMLTableSectionElement>>(({ className, ...props }, ref) => (
  <tfoot ref={ref} className={cn('bg-muted/60 border-t-2 border-[hsl(var(--pixel-border))] font-medium [&>tr]:last:border-b-0', className)} {...props} />
))
TableFooter.displayName = 'TableFooter'

const TableRow = React.forwardRef<HTMLTableRowElement, React.HTMLAttributes<HTMLTableRowElement>>(({ className, ...props }, ref) => (
  <tr ref={ref} className={cn('border-border data-[state=selected]:!bg-primary/15 md:hover:bg-muted/70 border-b transition-colors motion-reduce:transition-none', className)} {...props} />
))
TableRow.displayName = 'TableRow'

const TableHead = React.forwardRef<HTMLTableCellElement, React.ThHTMLAttributes<HTMLTableCellElement>>(({ className, ...props }, ref) => (
  <th
    ref={ref}
    className={cn(
      'text-muted-foreground h-11 px-3 text-left align-middle font-mono text-[11px] font-bold tracking-[0.12em] uppercase [&:has([role=checkbox])]:pr-0 [&>[role=checkbox]]:translate-y-[2px]',
      className,
    )}
    {...props}
  />
))
TableHead.displayName = 'TableHead'

const TableCell = React.forwardRef<HTMLTableCellElement, React.TdHTMLAttributes<HTMLTableCellElement>>(({ className, ...props }, ref) => (
  <td ref={ref} className={cn('h-11 px-3 py-2 align-middle [&:has([role=checkbox])]:pr-0 [&>[role=checkbox]]:translate-y-[2px]', className)} {...props} />
))
TableCell.displayName = 'TableCell'

const TableCaption = React.forwardRef<HTMLTableCaptionElement, React.HTMLAttributes<HTMLTableCaptionElement>>(({ className, ...props }, ref) => (
  <caption ref={ref} className={cn('text-muted-foreground mt-3 font-mono text-xs tracking-wide uppercase', className)} {...props} />
))
TableCaption.displayName = 'TableCaption'

export { Table, TableBody, TableCaption, TableCell, TableFooter, TableHead, TableHeader, TableRow }
