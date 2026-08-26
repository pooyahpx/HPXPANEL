import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import HpxPulseWizard from '@/features/hpx-pulse/wizard/hpx-pulse-wizard'
import {
  useDeleteHpxPulse,
  useGetHpxPulses,
  useRegeneratePulseTokens,
  type HpxPulseResponse,
} from '@/service/api/hpx-pulse'
import { useAdmin } from '@/hooks/use-admin'
import { hasPermission } from '@/utils/rbac'
import { Copy, Plus, RefreshCw, Trash2, Zap } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

function PulseCard({
  pulse,
  onDelete,
  onRegenerate,
}: {
  pulse: HpxPulseResponse
  onDelete: () => void
  onRegenerate: () => void
}) {
  const { t, i18n } = useTranslation()
  const fa = i18n.language?.startsWith('fa')
  const top = pulse.advice?.profiles.find(p => p.profile_id === pulse.profile_id)

  return (
    <Card className="space-y-3 p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <Zap className="text-primary size-4" />
            <span className="font-semibold">{pulse.name}</span>
            <Badge variant="outline">{pulse.status}</Badge>
          </div>
          <p className="text-muted-foreground mt-1 text-xs">
            {pulse.profile_id} · {pulse.carrier || '—'} · {pulse.preset}
          </p>
        </div>
        <div className="flex gap-1">
          <Button size="sm" variant="outline" onClick={onRegenerate}>
            {t('hpxPulse.regenerate', { defaultValue: 'Tokens' })}
          </Button>
          <Button size="sm" variant="destructive" onClick={onDelete}>
            <Trash2 className="size-3.5" />
          </Button>
        </div>
      </div>
      <div className="text-muted-foreground grid gap-1 text-xs sm:grid-cols-2">
        <span>IR {pulse.iran_public_ip} {pulse.iran_claimed ? '✓' : '…'}</span>
        <span>KH {pulse.abroad_public_ip} {pulse.abroad_claimed ? '✓' : '…'}</span>
        <span>{t('hpxPulse.tunnelPort', { defaultValue: 'Tunnel port' })}: {pulse.control_port}</span>
        {pulse.port_forwards?.length ? (
          <span>{t('hpxPulse.portForwards', { defaultValue: 'Port forwards' })}: {pulse.port_forwards.join(', ')}</span>
        ) : null}
      </div>
      {top && (
        <p className="text-xs">{fa ? top.title_fa : top.title}</p>
      )}
      {pulse.message && <p className="text-muted-foreground text-xs">{pulse.message}</p>}
    </Card>
  )
}

export default function HpxPulseList() {
  const { t } = useTranslation()
  const { admin } = useAdmin()
  const canCreate = hasPermission(admin, 'hpx_pulse', 'create')
  const canDelete = hasPermission(admin, 'hpx_pulse', 'delete')
  const { data, isLoading, refetch, isFetching } = useGetHpxPulses({ limit: 50, offset: 0 })
  const deleteMutation = useDeleteHpxPulse()
  const regenMutation = useRegeneratePulseTokens()
  const [wizardOpen, setWizardOpen] = useState(false)
  const [joinCommands, setJoinCommands] = useState<{ iran?: string; abroad?: string } | null>(null)

  useEffect(() => {
    const handler = () => setWizardOpen(true)
    window.addEventListener('openHpxPulseDialog', handler)
    return () => window.removeEventListener('openHpxPulseDialog', handler)
  }, [])

  const copy = async (text: string) => {
    await navigator.clipboard.writeText(text)
    toast.success(t('copied', { defaultValue: 'Copied' }))
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-muted-foreground text-sm">
          {t('hpxPulse.summary', {
            defaultValue: '{{total}} pulse tunnel(s)',
            total: data?.total ?? 0,
          })}
        </p>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
            <RefreshCw className={`size-3.5 ${isFetching ? 'animate-spin' : ''}`} />
          </Button>
          {canCreate && (
            <Button size="sm" onClick={() => setWizardOpen(true)}>
              <Plus className="size-3.5" />
              {t('hpxPulse.add', { defaultValue: 'New Pulse' })}
            </Button>
          )}
        </div>
      </div>

      {joinCommands && (
        <Card className="space-y-2 p-4 text-xs">
          <p className="font-medium">{t('hpxPulse.installCommands', { defaultValue: 'Install commands' })}</p>
          {joinCommands.iran && (
            <div className="space-y-1">
              <span className="text-muted-foreground">Iran</span>
              <pre className="bg-muted overflow-x-auto rounded p-2 font-mono text-[11px]">{joinCommands.iran}</pre>
              <Button size="sm" variant="secondary" onClick={() => copy(joinCommands.iran!)}>
                <Copy className="size-3" /> Iran
              </Button>
            </div>
          )}
          {joinCommands.abroad && (
            <div className="space-y-1">
              <span className="text-muted-foreground">Abroad</span>
              <pre className="bg-muted overflow-x-auto rounded p-2 font-mono text-[11px]">{joinCommands.abroad}</pre>
              <Button size="sm" variant="secondary" onClick={() => copy(joinCommands.abroad!)}>
                <Copy className="size-3" /> Abroad
              </Button>
            </div>
          )}
        </Card>
      )}

      {isLoading ? (
        <Skeleton className="h-32 w-full" />
      ) : (data?.pulses?.length ?? 0) === 0 ? (
        <Card className="text-muted-foreground p-8 text-center text-sm">
          {t('hpxPulse.empty', { defaultValue: 'No Pulse tunnels yet. Create one with the advisor wizard.' })}
        </Card>
      ) : (
        <div className="grid gap-3 lg:grid-cols-2">
          {data!.pulses.map(pulse => (
            <PulseCard
              key={pulse.id}
              pulse={pulse}
              onDelete={
                canDelete
                  ? async () => {
                      await deleteMutation.mutateAsync(pulse.id)
                      toast.success(t('deleted', { defaultValue: 'Deleted' }))
                    }
                  : () => {}
              }
              onRegenerate={async () => {
                const res = await regenMutation.mutateAsync(pulse.id)
                setJoinCommands({ iran: res.iran_join_command ?? undefined, abroad: res.abroad_join_command ?? undefined })
              }}
            />
          ))}
        </div>
      )}

      <HpxPulseWizard
        open={wizardOpen}
        onOpenChange={setWizardOpen}
        onCreated={res => {
          setJoinCommands({
            iran: res.iran_join_command ?? undefined,
            abroad: res.abroad_join_command ?? undefined,
          })
          refetch()
        }}
      />
    </div>
  )
}
