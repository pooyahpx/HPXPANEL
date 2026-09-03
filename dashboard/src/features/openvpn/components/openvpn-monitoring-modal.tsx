import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import { getOpenVPNNodeUsers, type OpenVPNNodeMonitoringResponse } from '@/service/api/openvpn-ops'
import { useQuery } from '@tanstack/react-query'
import { Activity, Loader2, RefreshCw, Shield } from 'lucide-react'
import { useTranslation } from 'react-i18next'

type OpenVPNMonitoringModalProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  nodeId: number | null
  nodeName?: string
}

export function OpenVPNMonitoringModal({ open, onOpenChange, nodeId, nodeName }: OpenVPNMonitoringModalProps) {
  const { t } = useTranslation()
  const { data, isLoading, isFetching, refetch, error } = useQuery({
    queryKey: ['openvpn-node-users', nodeId],
    queryFn: () => getOpenVPNNodeUsers(nodeId!),
    enabled: open && !!nodeId,
    refetchInterval: open ? 15000 : false,
  })

  const monitoring = data as OpenVPNNodeMonitoringResponse | undefined

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[90vh] max-w-2xl flex-col gap-4">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            {t('openvpn.monitoring.title')}
          </DialogTitle>
          <DialogDescription>
            {nodeName
              ? t('openvpn.monitoring.nodeInfo', { node: nodeName })
              : t('openvpn.monitoring.description')}
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-wrap items-center gap-2">
          {monitoring?.core_name && (
            <Badge variant="outline">
              {monitoring.core_name}
              {monitoring.listener_port ? ` · ${monitoring.listener_proto}/${monitoring.listener_port}` : ''}
            </Badge>
          )}
          {monitoring && (
            <Badge variant={monitoring.pki_ready ? 'secondary' : 'destructive'}>
              {monitoring.pki_ready ? t('openvpn.monitoring.pkiReady') : t('openvpn.monitoring.pkiMissing')}
            </Badge>
          )}
          <Button type="button" size="sm" variant="outline" className="ms-auto gap-1.5" onClick={() => void refetch()} disabled={isFetching}>
            <RefreshCw className={`h-3.5 w-3.5 ${isFetching ? 'animate-spin' : ''}`} />
            {t('openvpn.monitoring.refresh')}
          </Button>
        </div>

        <ScrollArea className="min-h-[280px] flex-1 rounded-md border">
          <div className="space-y-2 p-3">
            {isLoading && (
              <div className="text-muted-foreground flex items-center justify-center gap-2 py-10 text-sm">
                <Loader2 className="h-4 w-4 animate-spin" />
                {t('loading')}
              </div>
            )}
            {error && (
              <p className="text-destructive py-6 text-center text-sm">{t('openvpn.monitoring.loadError')}</p>
            )}
            {!isLoading && !error && monitoring?.users?.length === 0 && (
              <p className="text-muted-foreground py-6 text-center text-sm">{t('openvpn.monitoring.empty')}</p>
            )}
            {monitoring?.users?.map(user => (
              <div key={user.user_id} className="bg-muted/40 rounded-lg border p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium" dir="ltr">
                    {user.username}
                  </span>
                  <Badge variant={user.online ? 'default' : 'outline'} className="gap-1">
                    <Activity className="h-3 w-3" />
                    {user.online ? t('openvpn.monitoring.online') : t('openvpn.monitoring.offline')}
                  </Badge>
                  {!user.has_certificate && (
                    <Badge variant="destructive">{t('openvpn.monitoring.noCert')}</Badge>
                  )}
                </div>
                <div className="text-muted-foreground mt-2 space-y-1 font-mono text-[11px]" dir="ltr">
                  {user.serial && <p>serial: {user.serial}</p>}
                  {user.connection_count > 0 && <p>{t('openvpn.monitoring.sessions', { count: user.connection_count })}</p>}
                  {Object.keys(user.ips).length > 0 && (
                    <p>
                      IPs:{' '}
                      {Object.entries(user.ips)
                        .map(([ip, count]) => `${ip} (${count})`)
                        .join(', ')}
                    </p>
                  )}
                  {Object.entries(user.ip_protocol).map(([ip, proto]) => (
                    <p key={ip}>
                      {ip} · {proto || 'openvpn'}
                    </p>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  )
}
