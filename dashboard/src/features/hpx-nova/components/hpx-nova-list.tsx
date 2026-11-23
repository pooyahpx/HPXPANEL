import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { useAdmin } from '@/hooks/use-admin'
import { cn } from '@/lib/utils'
import {
  type HpxNovaActionResponse,
  type HpxNovaCarrier,
  type HpxNovaResponse,
  useCreateHpxNova,
  useDeleteHpxNova,
  useGetHpxNovas,
  useRegenerateNovaJoin,
  useSyncHpxNova,
} from '@/service/api/hpx-nova'
import { hasPermission } from '@/utils/rbac'
import { Copy, Orbit, Plus, RefreshCw, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

type JoinPayload = {
  iran?: string
  abroad?: string
  iranAlt?: string
  abroadAlt?: string
}

function statusTone(status: string) {
  if (status === 'running') return 'border-emerald-500/40 bg-emerald-500/10 text-emerald-500'
  if (status === 'partial' || status === 'pending_claim' || status === 'starting')
    return 'border-amber-500/40 bg-amber-500/10 text-amber-500'
  if (status === 'error' || status === 'unhealthy') return 'border-red-500/40 bg-red-500/10 text-red-500'
  return 'border-border bg-muted text-muted-foreground'
}

export default function HpxNovaList() {
  const { t } = useTranslation()
  const { admin } = useAdmin()
  const canCreate = hasPermission(admin, 'hpx_nova', 'create')
  const canUpdate = hasPermission(admin, 'hpx_nova', 'update')
  const canDelete = hasPermission(admin, 'hpx_nova', 'delete')
  const { data, isFetching, refetch } = useGetHpxNovas({ limit: 50, offset: 0 })
  const createNova = useCreateHpxNova()
  const deleteNova = useDeleteHpxNova()
  const regen = useRegenerateNovaJoin()
  const syncNova = useSyncHpxNova()

  const [open, setOpen] = useState(false)
  const [joinOpen, setJoinOpen] = useState(false)
  const [join, setJoin] = useState<JoinPayload>({})
  const [name, setName] = useState('')
  const [iranIp, setIranIp] = useState('')
  const [abroadIp, setAbroadIp] = useState('')
  const [carrier, setCarrier] = useState<HpxNovaCarrier>('wss')
  const [tunnelPort, setTunnelPort] = useState('8443')
  const [sni, setSni] = useState('www.cloudflare.com')
  const [forwards, setForwards] = useState('443')
  const [proxyListen, setProxyListen] = useState('127.0.0.1:1080')

  useEffect(() => {
    const openWizard = () => setOpen(true)
    window.addEventListener('openHpxNovaDialog', openWizard)
    return () => window.removeEventListener('openHpxNovaDialog', openWizard)
  }, [])

  const showJoin = (res: HpxNovaActionResponse) => {
    setJoin({
      iran: res.iran_join_command || undefined,
      abroad: res.abroad_join_command || undefined,
      iranAlt: res.iran_join_command_alt || undefined,
      abroadAlt: res.abroad_join_command_alt || undefined,
    })
    setJoinOpen(true)
  }

  const onCreate = async () => {
    try {
      const res = await createNova.mutateAsync({
        name: name.trim(),
        iran_public_ip: iranIp.trim(),
        abroad_public_ip: abroadIp.trim(),
        carrier,
        tunnel_port: Number(tunnelPort) || 8443,
        sni: sni.trim() || undefined,
        port_forwards: forwards
          .split(/[\n,]+/)
          .map(v => v.trim())
          .filter(Boolean),
        proxy_listen: proxyListen.trim() || null,
      })
      toast.success(res.detail || 'Nova created')
      setOpen(false)
      showJoin(res)
    } catch (e: any) {
      toast.error(e?.message || 'Create failed')
    }
  }

  const copy = async (text?: string) => {
    if (!text) return
    await navigator.clipboard.writeText(text)
    toast.success(t('copied', { defaultValue: 'Copied' }))
  }

  const novas = data?.novas ?? []

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4 p-4 md:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-display text-xl font-semibold tracking-tight">
            {t('hpxNova.title', { defaultValue: 'HPX Nova' })}
          </h2>
          <p className="text-muted-foreground text-sm">
            {t('hpxNova.subtitle', {
              defaultValue: 'Advanced Iran ↔ abroad tunnels on HPX NOVA TUNNEL ENGINE (isolated from Pulse).',
            })}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" className="cursor-pointer" onClick={() => refetch()} disabled={isFetching}>
            <RefreshCw className={cn('size-4', isFetching && 'animate-spin')} />
          </Button>
          {canCreate && (
            <Button size="sm" className="cursor-pointer gap-1.5" onClick={() => setOpen(true)}>
              <Plus className="size-4" />
              {t('hpxNova.new', { defaultValue: 'New Nova' })}
            </Button>
          )}
        </div>
      </div>

      {novas.length === 0 ? (
        <Card className="border-dashed p-10 text-center">
          <Orbit className="text-primary mx-auto mb-3 size-8 opacity-80" />
          <h3 className="text-lg font-semibold">{t('hpxNova.empty', { defaultValue: 'No Nova tunnels yet' })}</h3>
          <p className="text-muted-foreground mt-1 text-sm">
            {t('hpxNova.emptyHint', { defaultValue: 'Create one and run the join commands on Iran + Abroad.' })}
          </p>
        </Card>
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {novas.map((nova: HpxNovaResponse) => (
            <Card key={nova.id} className="border-white/10 bg-card/60 space-y-3 p-4">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-semibold">{nova.name}</p>
                  <p className="text-muted-foreground mt-1 font-mono text-[11px]" dir="ltr">
                    {nova.iran_public_ip} ↔ {nova.abroad_public_ip}:{nova.tunnel_port}
                  </p>
                </div>
                <Badge variant="outline" className={cn('uppercase', statusTone(nova.status))}>
                  {nova.status}
                </Badge>
              </div>
              <div className="text-muted-foreground flex flex-wrap gap-2 text-[11px]">
                <span className="rounded-md border px-2 py-0.5">{nova.carrier}</span>
                <span className="rounded-md border px-2 py-0.5">lanes {nova.lanes}</span>
                <span className="rounded-md border px-2 py-0.5">
                  IR {nova.iran_agent_online ? 'online' : nova.iran_claimed ? 'claimed' : '—'}
                </span>
                <span className="rounded-md border px-2 py-0.5">
                  AB {nova.abroad_agent_online ? 'online' : nova.abroad_claimed ? 'claimed' : '—'}
                </span>
              </div>
              {nova.message && <p className="text-muted-foreground line-clamp-2 text-xs">{nova.message}</p>}
              <div className="flex flex-wrap gap-2">
                {canUpdate && (
                  <>
                    <Button
                      size="sm"
                      variant="outline"
                      className="cursor-pointer"
                      onClick={async () => {
                        const res = await regen.mutateAsync(nova.id)
                        showJoin(res)
                      }}
                    >
                      Join cmds
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      className="cursor-pointer"
                      onClick={async () => {
                        await syncNova.mutateAsync(nova.id)
                        toast.success('Sync queued')
                      }}
                    >
                      Sync
                    </Button>
                  </>
                )}
                {canDelete && (
                  <Button
                    size="sm"
                    variant="destructive"
                    className="cursor-pointer"
                    onClick={async () => {
                      await deleteNova.mutateAsync(nova.id)
                      toast.success('Deleted')
                    }}
                  >
                    <Trash2 className="size-3.5" />
                  </Button>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{t('hpxNova.wizardTitle', { defaultValue: 'New HPX Nova tunnel' })}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label>Name</Label>
              <Input value={name} onChange={e => setName(e.target.value)} placeholder="nova-main" />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label>Iran public IP</Label>
                <Input value={iranIp} onChange={e => setIranIp(e.target.value)} dir="ltr" />
              </div>
              <div className="space-y-1.5">
                <Label>Abroad public IP</Label>
                <Input value={abroadIp} onChange={e => setAbroadIp(e.target.value)} dir="ltr" />
              </div>
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label>Carrier</Label>
                <Select value={carrier} onValueChange={v => setCarrier(v as HpxNovaCarrier)}>
                  <SelectTrigger className="cursor-pointer">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {(['wss', 'ws', 'quic', 'tcp', 'tls'] as HpxNovaCarrier[]).map(c => (
                      <SelectItem key={c} value={c}>
                        {c.toUpperCase()}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Tunnel port</Label>
                <Input value={tunnelPort} onChange={e => setTunnelPort(e.target.value)} dir="ltr" />
              </div>
            </div>
            <div className="space-y-1.5">
              <Label>SNI</Label>
              <Input value={sni} onChange={e => setSni(e.target.value)} dir="ltr" />
            </div>
            <div className="space-y-1.5">
              <Label>Port forwards (Iran listen)</Label>
              <Textarea value={forwards} onChange={e => setForwards(e.target.value)} placeholder={'443\n8443=127.0.0.1:8443'} dir="ltr" />
            </div>
            <div className="space-y-1.5">
              <Label>Local proxy (optional)</Label>
              <Input value={proxyListen} onChange={e => setProxyListen(e.target.value)} dir="ltr" />
            </div>
            <Button className="w-full cursor-pointer" onClick={onCreate} disabled={createNova.isPending || !name || !iranIp || !abroadIp}>
              Create Nova
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={joinOpen} onOpenChange={setJoinOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>{t('hpxNova.joinTitle', { defaultValue: 'Run on both servers' })}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {(
              [
                ['Iran', join.iran, join.iranAlt],
                ['Abroad', join.abroad, join.abroadAlt],
              ] as const
            ).map(([label, cmd, alt]) => (
              <div key={label} className="space-y-2">
                <p className="text-sm font-semibold">{label}</p>
                <div className="bg-muted/40 relative rounded-xl border p-3 font-mono text-[11px] break-all" dir="ltr">
                  {cmd || '—'}
                  <Button size="icon" variant="ghost" className="absolute end-1 top-1 size-7 cursor-pointer" onClick={() => copy(cmd)}>
                    <Copy className="size-3.5" />
                  </Button>
                </div>
                {alt && (
                  <div className="bg-muted/20 relative rounded-xl border border-dashed p-3 font-mono text-[11px] break-all" dir="ltr">
                    <span className="text-muted-foreground mb-1 block text-[10px] uppercase">Alt</span>
                    {alt}
                    <Button size="icon" variant="ghost" className="absolute end-1 top-1 size-7 cursor-pointer" onClick={() => copy(alt)}>
                      <Copy className="size-3.5" />
                    </Button>
                  </div>
                )}
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
