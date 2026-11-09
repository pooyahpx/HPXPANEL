import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import useDirDetection from '@/hooks/use-dir-detection'
import { cn } from '@/lib/utils'
import { useGetAllCores } from '@/service/api'
import { ArrowUpFromLine, Cpu } from 'lucide-react'
import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router'

export default function OutboundsPage() {
  const { t } = useTranslation()
  const dir = useDirDetection()
  const navigate = useNavigate()
  const { data, isLoading } = useGetAllCores({})

  const xrayCores = useMemo(() => (data?.cores ?? []).filter(core => String(core.type ?? 'xray') === 'xray'), [data?.cores])

  if (isLoading) {
    return (
      <div className="flex flex-col gap-3 p-4 md:p-6">
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    )
  }

  if (xrayCores.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 p-8 text-center">
        <ArrowUpFromLine className="text-muted-foreground h-10 w-10" />
        <p className="text-sm font-medium">{t('nodes.outbounds.emptyTitle', { defaultValue: 'No Xray cores yet' })}</p>
        <p className="text-muted-foreground max-w-sm text-xs">
          {t('nodes.outbounds.emptyHint', { defaultValue: 'Create an Xray core first, then manage outbounds like 3x-ui from here.' })}
        </p>
        <Button type="button" variant="outline" className="cursor-pointer" onClick={() => navigate('/nodes/cores/new?kind=xray')}>
          <Cpu className="h-4 w-4" />
          {t('settings.cores.addCore', { defaultValue: 'Add core' })}
        </Button>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3 p-4 md:p-6" dir={dir}>
      <div className="mb-1">
        <h2 className="text-base font-semibold">{t('nodes.outbounds.title', { defaultValue: 'Outbounds' })}</h2>
        <p className="text-muted-foreground text-xs">
          {t('nodes.outbounds.description', {
            defaultValue: 'Pick an Xray core to manage outbounds (tag, protocol, network, security, address, latency test) in the 3x-ui style.',
          })}
        </p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {xrayCores.map(core => (
          <Card
            key={core.id}
            role="button"
            tabIndex={0}
            className={cn('border-border hover:border-primary/40 cursor-pointer p-4 transition-colors')}
            onClick={() => navigate(`/nodes/cores/${core.id}?section=outbounds`)}
            onKeyDown={e => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                navigate(`/nodes/cores/${core.id}?section=outbounds`)
              }
            }}
          >
            <div className="flex items-start gap-3">
              <div className="bg-primary/10 text-primary flex h-9 w-9 shrink-0 items-center justify-center rounded-md">
                <ArrowUpFromLine className="h-4 w-4" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold">{core.name}</p>
                <p className="text-muted-foreground mt-0.5 font-mono text-[10px] tracking-wider uppercase">Xray · Outbounds</p>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}
