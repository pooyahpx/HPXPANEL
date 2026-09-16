import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { CORE_KIND_GROUPS, type CoreKindGroupId, type DashboardCoreKind } from '@/features/core-editor/kit/core-kind'
import { cn } from '@/lib/utils'
import { Check, ChevronDown } from 'lucide-react'
import { useTranslation } from 'react-i18next'

const GROUP_LABELS: Record<CoreKindGroupId, string> = {
  proxy: 'Proxy',
  wireguard: 'WireGuard',
  classicVpn: 'Classic VPN',
  overlay: 'Overlay',
}

const KIND_LABELS: Record<DashboardCoreKind, string> = {
  xray: 'Xray',
  wg: 'WireGuard',
  wg_c: 'WireGuard (Kernel)',
  amneziawg: 'AmneziaWG',
  openvpn: 'OpenVPN',
  ikev2: 'IKEv2 / IPsec',
  l2tp: 'L2TP / IPsec',
  pptp: 'PPTP',
  openconnect: 'OpenConnect',
  sstp: 'SSTP',
  ssh: 'SSH',
  gre: 'GRE',
  mtproto: 'MTProto',
}

export type CoreKindPickerProps = {
  value: DashboardCoreKind
  onChange: (kind: DashboardCoreKind) => void
  disabled?: boolean
  className?: string
  align?: 'start' | 'end'
}

/** Button → one flat restaurant-style list (grouped labels, no nested submenus). */
export function CoreKindPicker({ value, onChange, disabled, className, align = 'end' }: CoreKindPickerProps) {
  const { t } = useTranslation()

  const titleLabel = t('coreEditor.kindPicker.title', { defaultValue: 'Core type' })
  const chooseLabel = t('coreEditor.kindPicker.chooseType', { defaultValue: 'Choose core type' })
  const currentLabel = t(`coreTypes.${value}`, { defaultValue: KIND_LABELS[value] })

  const groupLabel = (id: CoreKindGroupId) =>
    t(`coreEditor.kindPicker.groups.${id}`, { defaultValue: GROUP_LABELS[id] })

  const kindLabel = (kind: DashboardCoreKind) => t(`coreTypes.${kind}`, { defaultValue: KIND_LABELS[kind] })

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          type="button"
          variant="outline"
          disabled={disabled}
          aria-label={chooseLabel}
          className={cn('h-10 min-w-[200px] justify-between gap-2 px-3 font-normal', className)}
        >
          <span className="min-w-0 flex-1 truncate text-start text-sm">{currentLabel}</span>
          <ChevronDown className="h-4 w-4 shrink-0 opacity-60" aria-hidden />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align={align} className="min-w-[240px] p-1.5" sideOffset={6}>
        <DropdownMenuLabel className="font-mono text-[10px] tracking-[0.14em] uppercase opacity-70">
          {titleLabel}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {CORE_KIND_GROUPS.map((group, groupIndex) => (
          <div key={group.id}>
            {groupIndex > 0 ? <DropdownMenuSeparator /> : null}
            <DropdownMenuLabel className="text-muted-foreground px-2.5 py-1.5 text-[10px] font-bold tracking-[0.12em] uppercase">
              {groupLabel(group.id)}
            </DropdownMenuLabel>
            {group.kinds.map(kind => {
              const selected = value === kind
              return (
                <DropdownMenuItem
                  key={kind}
                  disabled={disabled}
                  onSelect={() => onChange(kind)}
                  className={cn('min-h-9 py-1.5', selected && 'bg-primary/10')}
                >
                  <span className="min-w-0 flex-1 truncate">{kindLabel(kind)}</span>
                  {selected ? <Check className="text-primary h-4 w-4 shrink-0" aria-hidden /> : null}
                </DropdownMenuItem>
              )
            })}
          </div>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
