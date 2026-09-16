import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { ScrollArea } from '@/components/ui/scroll-area'
import { CORE_KIND_GROUPS, type DashboardCoreKind } from '@/features/core-editor/kit/core-kind'
import { cn } from '@/lib/utils'
import { Check, ChevronDown } from 'lucide-react'
import { useEffect, useId, useState } from 'react'
import { useTranslation } from 'react-i18next'

const SM_BREAKPOINT = 640

function useIsBelowSm() {
  const [isBelowSm, setIsBelowSm] = useState(false)

  useEffect(() => {
    const mql = window.matchMedia(`(max-width: ${SM_BREAKPOINT - 1}px)`)
    const onChange = () => setIsBelowSm(mql.matches)
    onChange()
    mql.addEventListener('change', onChange)
    return () => mql.removeEventListener('change', onChange)
  }, [])

  return isBelowSm
}

export type CoreKindPickerProps = {
  value: DashboardCoreKind
  onChange: (kind: DashboardCoreKind) => void
  disabled?: boolean
  className?: string
  align?: 'start' | 'end'
}

function KindOptionRow({
  kind,
  selected,
  disabled,
  onSelect,
}: {
  kind: DashboardCoreKind
  selected: boolean
  disabled?: boolean
  onSelect: (kind: DashboardCoreKind) => void
}) {
  const { t } = useTranslation()

  return (
    <button
      type="button"
      role="option"
      disabled={disabled}
      aria-selected={selected}
      onClick={() => onSelect(kind)}
      className={cn(
        'flex min-h-11 w-full items-start gap-2 rounded-none border-2 border-transparent px-3 py-2.5 text-start transition-colors duration-150',
        'hover:bg-accent/50 focus-visible:ring-ring focus-visible:ring-2 focus-visible:outline-none',
        'disabled:pointer-events-none disabled:opacity-50',
        selected && 'border-primary bg-primary/10',
      )}
    >
      <span className="min-w-0 flex-1 space-y-0.5">
        <span className="block text-sm font-medium leading-snug">{t(`coreTypes.${kind}`)}</span>
        <span className="text-muted-foreground block text-xs leading-snug">{t(`coreEditor.kindPicker.desc.${kind}`)}</span>
      </span>
      {selected ? <Check className="text-primary mt-0.5 h-4 w-4 shrink-0" aria-hidden /> : <span className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />}
    </button>
  )
}

function KindPickerPanel({
  value,
  disabled,
  onSelect,
  listId,
}: {
  value: DashboardCoreKind
  disabled?: boolean
  onSelect: (kind: DashboardCoreKind) => void
  listId: string
}) {
  const { t } = useTranslation()

  return (
    <ScrollArea className="h-[min(70dvh,28rem)] min-h-0 overscroll-contain" onWheelCapture={e => e.stopPropagation()} onTouchMoveCapture={e => e.stopPropagation()}>
      <div id={listId} role="listbox" aria-label={t('coreEditor.kindPicker.title', { defaultValue: 'Core type' })} className="flex flex-col gap-4 p-3">
        {CORE_KIND_GROUPS.map(group => (
          <section key={group.id} className="space-y-2">
            <h3 className="text-muted-foreground px-1 font-mono text-[10px] font-bold tracking-[0.14em] uppercase">
              {t(`coreEditor.kindPicker.groups.${group.id}`)}
            </h3>
            <div className="grid gap-2">
              {group.kinds.map(kind => (
                <KindOptionRow key={kind} kind={kind} selected={value === kind} disabled={disabled} onSelect={onSelect} />
              ))}
            </div>
          </section>
        ))}
      </div>
    </ScrollArea>
  )
}

export function CoreKindPicker({ value, onChange, disabled, className, align = 'end' }: CoreKindPickerProps) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const isBelowSm = useIsBelowSm()
  const listId = useId()

  const chooseLabel = t('coreEditor.kindPicker.chooseType', { defaultValue: 'Choose core type' })
  const titleLabel = t('coreEditor.kindPicker.title', { defaultValue: 'Core type' })
  const currentLabel = t(`coreTypes.${value}`)

  const handleSelect = (kind: DashboardCoreKind) => {
    onChange(kind)
    setOpen(false)
  }

  const trigger = (
    <Button
      type="button"
      variant="outline"
      role="combobox"
      aria-expanded={open}
      aria-haspopup="listbox"
      aria-controls={open ? listId : undefined}
      aria-label={chooseLabel}
      disabled={disabled}
      className={cn('h-10 min-w-[200px] justify-between gap-2 px-3 font-normal', className)}
    >
      <span className="min-w-0 flex-1 truncate text-start text-sm">{currentLabel}</span>
      <ChevronDown className={cn('h-4 w-4 shrink-0 opacity-60 transition-transform duration-150', open && 'rotate-180')} aria-hidden />
    </Button>
  )

  if (isBelowSm) {
    return (
      <>
        <Button
          type="button"
          variant="outline"
          role="combobox"
          aria-expanded={open}
          aria-haspopup="dialog"
          aria-label={chooseLabel}
          disabled={disabled}
          onClick={() => setOpen(true)}
          className={cn('h-10 min-w-[200px] justify-between gap-2 px-3 font-normal', className)}
        >
          <span className="min-w-0 flex-1 truncate text-start text-sm">{currentLabel}</span>
          <ChevronDown className={cn('h-4 w-4 shrink-0 opacity-60 transition-transform duration-150', open && 'rotate-180')} aria-hidden />
        </Button>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogContent className="flex max-h-[85dvh] w-[calc(100%-1.5rem)] max-w-md flex-col gap-0 overflow-hidden p-0 duration-200">
            <DialogHeader className="shrink-0 border-b px-4 py-3">
              <DialogTitle className="text-sm tracking-[0.08em]">{titleLabel}</DialogTitle>
            </DialogHeader>
            <KindPickerPanel value={value} disabled={disabled} onSelect={handleSelect} listId={listId} />
          </DialogContent>
        </Dialog>
      </>
    )
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>{trigger}</PopoverTrigger>
      <PopoverContent
        align={align}
        sideOffset={6}
        collisionPadding={8}
        className="w-[min(96vw,22rem)] max-w-[min(96vw,22rem)] p-0 duration-200"
        onWheel={e => e.stopPropagation()}
        onTouchMove={e => e.stopPropagation()}
      >
        <div className="border-b px-3 py-2">
          <p className="font-mono text-[10px] font-bold tracking-[0.14em] uppercase opacity-70">{titleLabel}</p>
        </div>
        <KindPickerPanel value={value} disabled={disabled} onSelect={handleSelect} listId={listId} />
      </PopoverContent>
    </Popover>
  )
}
