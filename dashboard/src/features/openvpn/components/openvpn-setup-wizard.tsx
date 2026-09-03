import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { getOpenVPNHealth, isOpenVPNPkiReady, runOpenVPNOnboarding } from '@/service/api/openvpn-ops'
import { useGetAllCores, useGetNodes } from '@/service/api'
import { CheckCircle2, ChevronLeft, ChevronRight, Loader2, TriangleAlert } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router'
import { toast } from 'sonner'

type OpenVPNSetupWizardProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
}

const STEPS = ['core', 'node', 'deploy', 'result'] as const
type Step = (typeof STEPS)[number]

export function OpenVPNSetupWizard({ open, onOpenChange }: OpenVPNSetupWizardProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [step, setStep] = useState<Step>('core')
  const [coreId, setCoreId] = useState<string>('')
  const [nodeId, setNodeId] = useState<string>('')
  const [groupName, setGroupName] = useState('OpenVPN Users')
  const [hostAddress, setHostAddress] = useState('')
  const [testUsername, setTestUsername] = useState('openvpn_test')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<Awaited<ReturnType<typeof runOpenVPNOnboarding>> | null>(null)

  const { data: coresData } = useGetAllCores({}, { query: { enabled: open } })
  const { data: nodesData } = useGetNodes({}, { query: { enabled: open } })

  const openvpnCores = useMemo(
    () => (coresData?.cores ?? []).filter(core => String(core.type) === 'openvpn'),
    [coresData?.cores],
  )

  const selectedCore = openvpnCores.find(core => String(core.id) === coreId)
  const pkiReady = isOpenVPNPkiReady(selectedCore?.config as Record<string, unknown>)

  const eligibleNodes = useMemo(() => {
    if (!coreId) return []
    return (nodesData?.nodes ?? []).filter(node => String(node.core_config_id) === coreId)
  }, [nodesData?.nodes, coreId])

  const reset = () => {
    setStep('core')
    setCoreId('')
    setNodeId('')
    setGroupName('OpenVPN Users')
    setHostAddress('')
    setTestUsername('openvpn_test')
    setResult(null)
  }

  const close = (next: boolean) => {
    onOpenChange(next)
    if (!next) reset()
  }

  const runDeploy = async () => {
    if (!coreId || !nodeId || !hostAddress.trim()) {
      toast.error(t('openvpn.wizard.missingFields'))
      return
    }
    setLoading(true)
    try {
      const response = await runOpenVPNOnboarding({
        core_id: Number(coreId),
        node_id: Number(nodeId),
        group_name: groupName,
        host_address: hostAddress.trim(),
        test_username: testUsername,
      })
      setResult(response)
      setStep('result')
      if (response.health.ready) {
        toast.success(t('openvpn.wizard.success'))
      } else {
        toast.warning(t('openvpn.wizard.partialSuccess'))
      }
    } catch (e: unknown) {
      const detail = (e as { data?: { detail?: string } })?.data?.detail || (e as Error)?.message
      toast.error(String(detail || t('openvpn.wizard.failed')))
    } finally {
      setLoading(false)
    }
  }

  const checkHealth = async () => {
    if (!coreId) return
    setLoading(true)
    try {
      const health = await getOpenVPNHealth({
        core_id: Number(coreId),
        node_id: nodeId ? Number(nodeId) : undefined,
      })
      if (health.ready) toast.success(t('openvpn.wizard.healthOk'))
      else toast.warning(health.issues.join(' · ') || t('openvpn.wizard.healthIssues'))
    } catch (e: unknown) {
      toast.error((e as Error)?.message || t('openvpn.wizard.healthFailed'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent className="max-h-[90vh] max-w-lg overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{t('openvpn.wizard.title')}</DialogTitle>
          <DialogDescription>{t('openvpn.wizard.description')}</DialogDescription>
        </DialogHeader>

        {step === 'core' && (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>{t('openvpn.wizard.selectCore')}</Label>
              <Select value={coreId} onValueChange={setCoreId}>
                <SelectTrigger>
                  <SelectValue placeholder={t('openvpn.wizard.selectCorePlaceholder')} />
                </SelectTrigger>
                <SelectContent>
                  {openvpnCores.map(core => (
                    <SelectItem key={core.id} value={String(core.id)}>
                      {core.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {!openvpnCores.length && (
              <Alert>
                <TriangleAlert className="h-4 w-4" />
                <AlertTitle>{t('openvpn.wizard.noCoreTitle')}</AlertTitle>
                <AlertDescription>{t('openvpn.wizard.noCoreHint')}</AlertDescription>
              </Alert>
            )}
            {selectedCore && (
              <Alert variant={pkiReady ? 'default' : 'destructive'}>
                {pkiReady ? <CheckCircle2 className="h-4 w-4" /> : <TriangleAlert className="h-4 w-4" />}
                <AlertTitle>{pkiReady ? t('openvpn.wizard.pkiReady') : t('openvpn.wizard.pkiMissingTitle')}</AlertTitle>
                <AlertDescription>
                  {pkiReady ? t('openvpn.wizard.pkiReadyHint') : t('openvpn.wizard.pkiMissingHint')}
                </AlertDescription>
              </Alert>
            )}
            <div className="flex flex-wrap gap-2">
              <Button type="button" variant="outline" onClick={() => navigate('/nodes/cores/new?kind=openvpn')}>
                {t('openvpn.wizard.createCore')}
              </Button>
              {selectedCore && (
                <Button type="button" variant="outline" onClick={() => navigate(`/nodes/cores/${selectedCore.id}`)}>
                  {t('openvpn.wizard.editCore')}
                </Button>
              )}
              <Button type="button" className="ms-auto" disabled={!coreId || !pkiReady} onClick={() => setStep('node')}>
                {t('openvpn.wizard.next')}
                <ChevronRight className="ms-1 h-4 w-4" />
              </Button>
            </div>
          </div>
        )}

        {step === 'node' && (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>{t('openvpn.wizard.selectNode')}</Label>
              <Select value={nodeId} onValueChange={setNodeId}>
                <SelectTrigger>
                  <SelectValue placeholder={t('openvpn.wizard.selectNodePlaceholder')} />
                </SelectTrigger>
                <SelectContent>
                  {eligibleNodes.map(node => (
                    <SelectItem key={node.id} value={String(node.id)}>
                      {node.name} ({node.status})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {!eligibleNodes.length && (
              <Alert>
                <TriangleAlert className="h-4 w-4" />
                <AlertDescription>{t('openvpn.wizard.noNodeHint')}</AlertDescription>
              </Alert>
            )}
            <div className="flex gap-2">
              <Button type="button" variant="outline" onClick={() => setStep('core')}>
                <ChevronLeft className="me-1 h-4 w-4" />
                {t('openvpn.wizard.back')}
              </Button>
              <Button type="button" variant="outline" onClick={() => void checkHealth()} disabled={!coreId || loading}>
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : t('openvpn.wizard.healthCheck')}
              </Button>
              <Button type="button" className="ms-auto" disabled={!nodeId} onClick={() => setStep('deploy')}>
                {t('openvpn.wizard.next')}
                <ChevronRight className="ms-1 h-4 w-4" />
              </Button>
            </div>
          </div>
        )}

        {step === 'deploy' && (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="ovpn-group">{t('openvpn.wizard.groupName')}</Label>
              <Input id="ovpn-group" value={groupName} onChange={e => setGroupName(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="ovpn-host">{t('openvpn.wizard.hostAddress')}</Label>
              <Input id="ovpn-host" value={hostAddress} onChange={e => setHostAddress(e.target.value)} placeholder="203.0.113.10" dir="ltr" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="ovpn-user">{t('openvpn.wizard.testUser')}</Label>
              <Input id="ovpn-user" value={testUsername} onChange={e => setTestUsername(e.target.value)} dir="ltr" />
            </div>
            <p className="text-muted-foreground text-xs">{t('openvpn.wizard.deployHint')}</p>
            <div className="flex gap-2">
              <Button type="button" variant="outline" onClick={() => setStep('node')}>
                <ChevronLeft className="me-1 h-4 w-4" />
                {t('openvpn.wizard.back')}
              </Button>
              <Button type="button" className="ms-auto" disabled={loading} onClick={() => void runDeploy()}>
                {loading ? <Loader2 className="me-2 h-4 w-4 animate-spin" /> : null}
                {t('openvpn.wizard.deploy')}
              </Button>
            </div>
          </div>
        )}

        {step === 'result' && result && (
          <div className="space-y-4">
            <Alert variant={result.health.ready ? 'default' : 'destructive'}>
              {result.health.ready ? <CheckCircle2 className="h-4 w-4" /> : <TriangleAlert className="h-4 w-4" />}
              <AlertTitle>{result.health.ready ? t('openvpn.wizard.doneTitle') : t('openvpn.wizard.donePartial')}</AlertTitle>
              <AlertDescription>
                <div className="space-y-1 pt-1 text-xs">
                  <p>
                    {t('openvpn.wizard.createdUser')}: <span dir="ltr">{result.username}</span>
                  </p>
                  {result.subscription_url && (
                    <p className="break-all" dir="ltr">
                      {result.subscription_url}/openvpn
                    </p>
                  )}
                </div>
              </AlertDescription>
            </Alert>
            {result.health.issues.length > 0 && (
              <ul className="text-muted-foreground list-disc space-y-1 ps-5 text-xs">
                {result.health.issues.map(issue => (
                  <li key={issue}>{issue}</li>
                ))}
              </ul>
            )}
            <div className="flex flex-wrap gap-2">
              <Badge variant="outline">group #{result.group_id}</Badge>
              <Badge variant="outline">host #{result.host_id}</Badge>
              <Badge variant="outline">user #{result.user_id}</Badge>
            </div>
            <Button type="button" className="w-full" onClick={() => close(false)}>
              {t('openvpn.wizard.close')}
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
