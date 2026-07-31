import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { ListColumn } from '@/components/common/list-generator'
import { CoreResponse } from '@/service/api'
import CoreActionsMenu from '@/features/nodes/components/cores/core-actions-menu'
import { Badge } from '@/components/ui/badge'
import { Network, ShieldCheck } from 'lucide-react'

interface UseCoresListColumnsProps {
  onEdit: (core: CoreResponse) => void
  onDuplicate?: (coreId: number | string) => void
  onDelete?: (coreName: string, coreId: number) => void
  canUpdate?: boolean
  canCreate?: boolean
  canDelete?: boolean
}

export const useCoresListColumns = ({ onEdit, onDuplicate, onDelete, canUpdate = true, canCreate = true, canDelete = true }: UseCoresListColumnsProps) => {
  const { t } = useTranslation()

  return useMemo<ListColumn<CoreResponse>[]>(
    () => [
      {
        id: 'name',
        header: t('name', { defaultValue: 'Name' }),
        width: '2.5fr',
        cell: core => (
          <div className="flex min-w-0 items-center gap-2">
            <span className="h-2 w-2 shrink-0 rounded-full bg-green-500" />
            <span className="truncate font-medium">{core.name}</span>
          </div>
        ),
      },
      {
        id: 'type',
        header: t('core.type', { defaultValue: 'Type' }),
        width: '1.5fr',
        hideOnMobile: true,
        cell: core => {
          const type = String(core.type ?? 'xray')
          const Icon = type === 'ikev2' ? ShieldCheck : type === 'l2tp' ? Network : null
          return (
            <Badge variant="outline" className="w-fit gap-1.5">
              {Icon && <Icon className="h-3.5 w-3.5" />}
              {t(`coreTypes.${type}`, { defaultValue: type === 'wg' ? 'WireGuard' : type === 'xray' ? 'Xray' : type.toUpperCase() })}
            </Badge>
          )
        },
      },
      ...(canUpdate || canCreate || canDelete
        ? [
            {
              id: 'actions',
              header: '',
              width: '24px',
              align: 'end' as const,
              hideOnMobile: false,
              cell: (core: CoreResponse) => (
                <CoreActionsMenu
                  core={core}
                  onEdit={onEdit}
                  onDuplicate={canCreate && onDuplicate ? () => onDuplicate(core.id) : undefined}
                  onDelete={canDelete && onDelete ? () => onDelete(core.name, core.id) : undefined}
                  canUpdate={canUpdate}
                  canCreate={canCreate}
                  canDelete={canDelete}
                />
              ),
            },
          ]
        : []),
    ],
    [t, onEdit, onDuplicate, onDelete, canUpdate, canCreate, canDelete],
  )
}
