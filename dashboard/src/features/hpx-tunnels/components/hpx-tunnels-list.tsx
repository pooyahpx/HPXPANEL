import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useAdmin } from '@/hooks/use-admin'
import HpxTunnelCard from '@/features/hpx-tunnels/components/hpx-tunnel-card'
import HpxTunnelModal from '@/features/hpx-tunnels/dialogs/hpx-tunnel-modal'
import { hpxTunnelFormDefaultValues } from '@/features/hpx-tunnels/forms/hpx-tunnel-form'
import {
  type HpxTunnelResponse,
  useGetHpxTunnels,
  useRestartHpxTunnel,
  useStartHpxTunnel,
  useStopHpxTunnel,
} from '@/service/api/hpx-tunnels'
import { hasPermission } from '@/utils/rbac'
import { zodResolver } from '@hookform/resolvers/zod'
import type { ComponentType } from 'react'
import { Plus, Radar, RefreshCw, ShieldCheck } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { hpxTunnelFormFromResponse, hpxTunnelFormSchema, type HpxTunnelFormValues } from '@/features/hpx-tunnels/forms/hpx-tunnel-form'

export default function HpxTunnelsList() {
  const { t } = useTranslation()
  const { admin } = useAdmin()
  const canCreate = hasPermission(admin, 'hpx_tunnels', 'create')
  const canStart = hasPermission(admin, 'hpx_tunnels', 'start')
  const { data, isLoading, isFetching, refetch } = useGetHpxTunnels({ limit: 100, offset: 0 }, { refetchInterval: 15000 })
  const startMutation = useStartHpxTunnel()
  const stopMutation = useStopHpxTunnel()
  const restartMutation = useRestartHpxTunnel()
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingTunnel, setEditingTunnel] = useState<HpxTunnelResponse | null>(null)

  const form = useForm<HpxTunnelFormValues>({
    resolver: zodResolver(hpxTunnelFormSchema),
    defaultValues: hpxTunnelFormDefaultValues(),
  })

  useEffect(() => {
    const handler = () => {
      setEditingTunnel(null)
      form.reset(hpxTunnelFormDefaultValues())
      setDialogOpen(true)
    }
    window.addEventListener('openHpxTunnelDialog', handler)
    return () => window.removeEventListener('openHpxTunnelDialog', handler)
  }, [form])

  const summary = useMemo(() => {
    const tunnels = data?.tunnels ?? []
    return {
      total: tunnels.length,
      running: tunnels.filter(item => item.status === 'running').length,
      unhealthy: tunnels.filter(item => item.status === 'unhealthy' || item.status === 'error').length,
    }
  }, [data?.tunnels])

  const actionLoading = startMutation.isPending || stopMutation.isPending || restartMutation.isPending

  const runAction = async (label: string, fn: () => Promise<{ message?: string | null }>) => {
    try {
      const result = await fn()
      toast.success(label, { description: result.message || undefined })
      await refetch()
    } catch (error: any) {
      toast.error(label, { description: error?.data?.detail || error?.message })
    }
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 p-4 md:p-6">
      <div className="grid gap-3 md:grid-cols-3">
        <SummaryTile icon={Radar} label={t('hpxTunnel.summary.total', { defaultValue: 'Tunnels' })} value={String(summary.total)} />
        <SummaryTile icon={ShieldCheck} label={t('hpxTunnel.summary.running', { defaultValue: 'Running' })} value={String(summary.running)} tone="success" />
        <SummaryTile icon={RefreshCw} label={t('hpxTunnel.summary.unhealthy', { defaultValue: 'Issues' })} value={String(summary.unhealthy)} tone={summary.unhealthy > 0 ? 'danger' : undefined} />
      </div>

      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-muted-foreground text-sm">{t('hpxTunnel.description', { defaultValue: 'Manage encrypted ICMP tunnels powered by HPX (ChaCha20).' })}</p>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
            <RefreshCw className={isFetching ? 'size-4 animate-spin' : 'size-4'} />
            {t('refresh', { defaultValue: 'Refresh' })}
          </Button>
          {canCreate && (
            <Button
              size="sm"
              onClick={() => {
                setEditingTunnel(null)
                form.reset(hpxTunnelFormDefaultValues())
                setDialogOpen(true)
              }}
            >
              <Plus className="size-4" />
              {t('hpxTunnel.addTunnel', { defaultValue: 'Add tunnel' })}
            </Button>
          )}
        </div>
      </div>

      {isLoading ? (
        <div className="grid gap-4">
          {[1, 2].map(item => (
            <Skeleton key={item} className="h-44 w-full rounded-xl" />
          ))}
        </div>
      ) : (data?.tunnels.length ?? 0) === 0 ? (
        <Card className="flex flex-col items-center justify-center gap-3 border-dashed px-6 py-16 text-center">
          <Radar className="text-muted-foreground size-10" />
          <div>
            <h3 className="text-lg font-semibold">{t('hpxTunnel.emptyTitle', { defaultValue: 'No ICMP tunnels yet' })}</h3>
            <p className="text-muted-foreground mt-1 max-w-md text-sm">
              {t('hpxTunnel.emptyDescription', {
                defaultValue: 'Create an IRAN (client) or FOREIGN (server) tunnel to bridge traffic over encrypted ping packets.',
              })}
            </p>
          </div>
          {canCreate && (
            <Button
              onClick={() => {
                setEditingTunnel(null)
                form.reset(hpxTunnelFormDefaultValues())
                setDialogOpen(true)
              }}
            >
              <Plus className="size-4" />
              {t('hpxTunnel.addTunnel', { defaultValue: 'Add tunnel' })}
            </Button>
          )}
        </Card>
      ) : (
        <div className="grid gap-4">
          {data?.tunnels.map(tunnel => (
            <HpxTunnelCard
              key={tunnel.id}
              tunnel={tunnel}
              actionLoading={actionLoading || !canStart}
              onEdit={item => {
                setEditingTunnel(item)
                form.reset(hpxTunnelFormFromResponse(item))
                setDialogOpen(true)
              }}
              onStart={id => runAction(t('hpxTunnel.start', { defaultValue: 'Start' }), () => startMutation.mutateAsync(id))}
              onStop={id => runAction(t('hpxTunnel.stop', { defaultValue: 'Stop' }), () => stopMutation.mutateAsync(id))}
              onRestart={id => runAction(t('hpxTunnel.restart', { defaultValue: 'Restart' }), () => restartMutation.mutateAsync(id))}
            />
          ))}
        </div>
      )}

      <HpxTunnelModal open={dialogOpen} onOpenChange={setDialogOpen} form={form} editingTunnel={editingTunnel} onSuccess={() => refetch()} />
    </div>
  )
}

function SummaryTile({
  icon: Icon,
  label,
  value,
  tone,
}: {
  icon: ComponentType<{ className?: string }>
  label: string
  value: string
  tone?: 'success' | 'danger'
}) {
  return (
    <Card className="flex items-center gap-3 px-4 py-3">
      <div className="bg-primary/10 text-primary rounded-lg p-2">
        <Icon className="size-5" />
      </div>
      <div>
        <div className="text-muted-foreground text-xs uppercase tracking-wide">{label}</div>
        <div className={tone === 'danger' ? 'text-destructive text-2xl font-bold tabular-nums' : tone === 'success' ? 'text-emerald-600 text-2xl font-bold tabular-nums' : 'text-2xl font-bold tabular-nums'}>
          {value}
        </div>
      </div>
    </Card>
  )
}
