import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import useDirDetection from '@/hooks/use-dir-detection'
import { cn } from '@/lib/utils'
import { useGetCoresSimple, useGetHosts, useGetNodesSimple, useGetSystemUsersStats } from '@/service/api'
import { Check, Circle, Cpu, ListChecks, Server, Share2, UserPlus, X } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router'

const DISMISS_KEY = 'hpxpanel.setupChecklist.dismissed'

type SetupChecklistCardProps = {
  onCreateNode?: () => void
  onCreateCore?: () => void
  onCreateHost?: () => void
  onCreateUser?: () => void
  canCreateNode?: boolean
  canCreateCore?: boolean
  canCreateHost?: boolean
  canCreateUser?: boolean
}

type StepId = 'node' | 'core' | 'host' | 'user' | 'test'

type StepConfig = {
  id: StepId
  titleKey: string
  descriptionKey: string
  icon: typeof Server
  done: boolean
  actionLabelKey: string
  onAction?: () => void
  showAction: boolean
}

const SetupChecklistCard = ({
  onCreateNode,
  onCreateCore,
  onCreateHost,
  onCreateUser,
  canCreateNode = false,
  canCreateCore = false,
  canCreateHost = false,
  canCreateUser = false,
}: SetupChecklistCardProps) => {
  const { t } = useTranslation()
  const dir = useDirDetection()
  const navigate = useNavigate()
  const [dismissed, setDismissed] = useState(() => {
    try {
      return localStorage.getItem(DISMISS_KEY) === '1'
    } catch {
      return false
    }
  })

  const canShow = canCreateNode && canCreateUser

  const { data: nodesData, isLoading: nodesLoading } = useGetNodesSimple({ all: true }, { query: { enabled: canShow && !dismissed } })
  const { data: coresData, isLoading: coresLoading } = useGetCoresSimple({ all: true }, { query: { enabled: canShow && !dismissed } })
  const { data: hostsData, isLoading: hostsLoading } = useGetHosts(undefined, { query: { enabled: canShow && !dismissed } })
  const { data: usersStats, isLoading: usersLoading } = useGetSystemUsersStats(undefined, { query: { enabled: canShow && !dismissed } })

  const hasNode = (nodesData?.total ?? 0) > 0
  const hasCore = (coresData?.total ?? 0) > 0
  const hasHost = (hostsData?.length ?? 0) > 0
  const hasUser = (usersStats?.total_user ?? 0) > 0
  const isLoading = nodesLoading || coresLoading || hostsLoading || usersLoading

  const steps = useMemo<StepConfig[]>(
    () => [
      {
        id: 'node',
        titleKey: 'setupChecklist.steps.node.title',
        descriptionKey: 'setupChecklist.steps.node.description',
        icon: Server,
        done: hasNode,
        actionLabelKey: 'setupChecklist.steps.node.action',
        onAction: onCreateNode,
        showAction: canCreateNode,
      },
      {
        id: 'core',
        titleKey: 'setupChecklist.steps.core.title',
        descriptionKey: 'setupChecklist.steps.core.description',
        icon: Cpu,
        done: hasCore,
        actionLabelKey: 'setupChecklist.steps.core.action',
        onAction: onCreateCore ?? (() => navigate('/nodes/cores/new')),
        showAction: canCreateCore,
      },
      {
        id: 'host',
        titleKey: 'setupChecklist.steps.host.title',
        descriptionKey: 'setupChecklist.steps.host.description',
        icon: Share2,
        done: hasHost,
        actionLabelKey: 'setupChecklist.steps.host.action',
        onAction: onCreateHost,
        showAction: canCreateHost,
      },
      {
        id: 'user',
        titleKey: 'setupChecklist.steps.user.title',
        descriptionKey: 'setupChecklist.steps.user.description',
        icon: UserPlus,
        done: hasUser,
        actionLabelKey: 'setupChecklist.steps.user.action',
        onAction: onCreateUser,
        showAction: canCreateUser,
      },
      {
        id: 'test',
        titleKey: 'setupChecklist.steps.test.title',
        descriptionKey: hasUser ? 'setupChecklist.steps.test.tip' : 'setupChecklist.steps.test.description',
        icon: ListChecks,
        done: hasUser,
        actionLabelKey: 'setupChecklist.steps.test.action',
        onAction: () => navigate('/users'),
        showAction: hasUser,
      },
    ],
    [canCreateCore, canCreateHost, canCreateNode, canCreateUser, hasCore, hasHost, hasNode, hasUser, navigate, onCreateCore, onCreateHost, onCreateNode, onCreateUser],
  )

  const completedCount = steps.filter(step => step.done).length
  const progress = Math.round((completedCount / steps.length) * 100)
  const allComplete = completedCount === steps.length

  const handleDismiss = () => {
    try {
      localStorage.setItem(DISMISS_KEY, '1')
    } catch {
      // ignore storage failures
    }
    setDismissed(true)
  }

  if (!canShow || dismissed || (!isLoading && allComplete)) return null

  return (
    <Card className="bg-card/80 border" dir={dir}>
      <CardHeader className="p-2">
        <div className="flex w-full items-start justify-between gap-2">
          <div className="flex min-w-0 items-start gap-2 p-2 text-left">
            <div className="bg-primary/10 rounded-md p-1.5">
              <ListChecks className="text-primary h-4 w-4" />
            </div>
            <div className="min-w-0">
              <CardTitle className={cn(dir === 'rtl' && 'text-right', 'truncate text-sm font-semibold')}>
                {t('setupChecklist.title', { defaultValue: 'First-run setup' })}
              </CardTitle>
              <p className="text-muted-foreground truncate text-xs">
                {t('setupChecklist.subtitle', { defaultValue: 'Connect a node, add a core and host, then create a user' })}
              </p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="mt-1 h-8 w-8 shrink-0"
            onClick={handleDismiss}
            aria-label={t('setupChecklist.dismiss', { defaultValue: 'Dismiss' })}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3 px-4 pb-4">
        <div className="space-y-1.5">
          <div className="text-muted-foreground flex items-center justify-between text-xs">
            <span>{t('setupChecklist.progress', { defaultValue: '{{done}} of {{total}} complete', done: completedCount, total: steps.length })}</span>
            <span className="font-mono tabular-nums">{progress}%</span>
          </div>
          <Progress value={isLoading ? 0 : progress} className="h-1.5 rounded-none" indicatorClassName="rounded-none" />
        </div>

        <div className="space-y-2">
          {steps.map(step => {
            const Icon = step.icon
            return (
              <div key={step.id} className="bg-muted/20 flex flex-wrap items-center justify-between gap-2 rounded-none border px-3 py-2">
                <div className="flex min-w-0 items-start gap-2">
                  <div className={cn('mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center border', step.done ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-600' : 'bg-muted/40 text-muted-foreground')}>
                    {step.done ? <Check className="h-3.5 w-3.5" /> : <Circle className="h-3 w-3" />}
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5">
                      <Icon className="text-muted-foreground h-3.5 w-3.5 shrink-0" />
                      <p className="text-sm font-medium">{t(step.titleKey)}</p>
                    </div>
                    <p className="text-muted-foreground text-xs">{t(step.descriptionKey)}</p>
                  </div>
                </div>
                {!step.done && step.showAction && step.onAction ? (
                  <Button size="sm" variant="outline" className="h-8 shrink-0" onClick={step.onAction}>
                    {t(step.actionLabelKey)}
                  </Button>
                ) : null}
              </div>
            )
          })}
        </div>
      </CardContent>
    </Card>
  )
}

export default SetupChecklistCard
