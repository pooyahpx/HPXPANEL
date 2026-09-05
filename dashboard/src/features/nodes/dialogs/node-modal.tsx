import { DecimalInput } from '@/components/common/decimal-input'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import useDirDetection from '@/hooks/use-dir-detection'
import useDynamicErrorHandler from '@/hooks/use-dynamic-errors.ts'
import { cn } from '@/lib/utils'
import { CoresSimpleResponse, DataLimitResetStrategy, getNode, NodeConnectionType, NodeResponse, useCreateNode, useGetNode, useModifyNode } from '@/service/api'
import { formatBytes, gbToBytes } from '@/utils/formatByte'
import { queryClient } from '@/utils/query-client'
import { Cable, Loader2, RefreshCw, Settings, Server, Pencil, Shield } from 'lucide-react'
import React, { useEffect, useRef, useState } from 'react'
import { UseFormReturn } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { v4 as uuidv4 } from 'uuid'
import { LoaderButton } from '@/components/ui/loader-button'
import type { NodeFormValues } from '@/features/nodes/forms/node-form'
import type { CoreSimple } from '@/service/api'

interface NodeModalProps {
  isDialogOpen: boolean
  onOpenChange: (open: boolean) => void
  form: UseFormReturn<NodeFormValues>
  editingNode: boolean
  editingNodeId?: number
  initialNodeData?: NodeResponse
  coresData?: CoresSimpleResponse
  onSuccess?: () => void
}

export default function NodeModal({ isDialogOpen, onOpenChange, form, editingNode, editingNodeId, initialNodeData, coresData, onSuccess }: NodeModalProps) {
  const { t } = useTranslation()
  const dir = useDirDetection()
  const addNodeMutation = useCreateNode()
  const modifyNodeMutation = useModifyNode()
  const handleError = useDynamicErrorHandler()
  const cores = coresData?.cores
  const isLoadingCores = false
  const [statusChecking, setStatusChecking] = useState(false)
  const [errorDetails, setErrorDetails] = useState<string | null>(null)
  const [autoCheck, setAutoCheck] = useState(false)
  const [showErrorDetails, setShowErrorDetails] = useState(false)
  const [debouncedValues, setDebouncedValues] = useState<NodeFormValues | null>(null)
  const [isFetchingNodeData, setIsFetchingNodeData] = useState(false)
  const [deckTab, setDeckTab] = useState<'link' | 'trust' | 'advanced'>('link')

  const { data: node, refetch: refetchNode } = useGetNode(
    editingNodeId || 0,
    editingNode && editingNodeId
      ? {
          query: {
            enabled: editingNode && !!editingNodeId && isDialogOpen,
            initialData: initialNodeData,
            refetchInterval: 5000,
            refetchOnMount: false,
            staleTime: 0,
            gcTime: 0,
          },
        }
      : { query: { enabled: false } },
  )

  const currentNode = node || initialNodeData
  const lastSyncedNodeRef = useRef<NodeResponse | null>(null)

  useEffect(() => {
    if (isDialogOpen) {
      setErrorDetails(null)
      setAutoCheck(true)
      setIsFetchingNodeData(false)
      setDeckTab('link')
      lastSyncedNodeRef.current = null
    }
  }, [isDialogOpen])

  // Update form when node data changes (from auto-refresh or external updates)
  useEffect(() => {
    if (!isDialogOpen || !editingNode || !editingNodeId || !node) return

    // Skip if form is dirty (user has made changes)
    if (form.formState.isDirty) return

    // Skip if this is the same node data we already synced
    // Compare key fields that change externally (status, message, versions, usage)
    const lastSynced = lastSyncedNodeRef.current
    if (
      lastSynced &&
      lastSynced.id === node.id &&
      lastSynced.status === node.status &&
      lastSynced.message === node.message &&
      (lastSynced.core_version ?? lastSynced.xray_version) === (node.core_version ?? node.xray_version) &&
      lastSynced.node_version === node.node_version &&
      lastSynced.uplink === node.uplink &&
      lastSynced.downlink === node.downlink &&
      lastSynced.name === node.name &&
      lastSynced.address === node.address &&
      lastSynced.port === node.port
    ) {
      return
    }

    // Update form with new node data
    const dataLimitBytes = node.data_limit ?? null
    const dataLimitGB = dataLimitBytes !== null && dataLimitBytes !== undefined && dataLimitBytes > 0 ? dataLimitBytes / (1024 * 1024 * 1024) : 0

    form.reset(
      {
        name: node.name,
        address: node.address,
        port: node.port,
        api_port: node.api_port ?? null,
        usage_coefficient: node.usage_coefficient,
        connection_type: node.connection_type,
        server_ca: node.server_ca,
        keep_alive: node.keep_alive,
        keep_alive_unit: 'seconds',
        api_key: (node.api_key as string) || '',
        core_config_id: node.core_config_id ?? cores?.[0]?.id,
        data_limit: dataLimitGB,
        data_limit_reset_strategy: node.data_limit_reset_strategy ?? DataLimitResetStrategy.no_reset,
        reset_time: node.reset_time ?? null,
        default_timeout: node.default_timeout ?? 10,
        internal_timeout: node.internal_timeout ?? 15,
        proxy_url: node.proxy_url ?? '',
      },
      { keepDirty: false, keepValues: false },
    )

    lastSyncedNodeRef.current = node
  }, [node, isDialogOpen, editingNode, editingNodeId, form, cores])

  useEffect(() => {
    const values = form.getValues()
    const timer = setTimeout(() => {
      setDebouncedValues(values)
    }, 1000)

    return () => clearTimeout(timer)
  }, [form.watch('name'), form.watch('address'), form.watch('port'), form.watch('api_key')])

  useEffect(() => {
    if (!isDialogOpen || !autoCheck || editingNode || !debouncedValues) return

    const { name, address, port, api_key } = debouncedValues
    if (name && address && port && api_key) {
      checkNodeStatus()
    }
  }, [debouncedValues])

  useEffect(() => {
    if (editingNode && isDialogOpen && editingNodeId) {
      checkNodeStatus()
    }
  }, [editingNode, isDialogOpen, editingNodeId])
  useEffect(() => {
    if (editingNode && editingNodeId) {
      if (initialNodeData) {
        const nodeData = initialNodeData

        const dataLimitBytes = nodeData.data_limit ?? null
        const dataLimitGB = dataLimitBytes !== null && dataLimitBytes !== undefined && dataLimitBytes > 0 ? dataLimitBytes / (1024 * 1024 * 1024) : 0

        form.reset({
          name: nodeData.name,
          address: nodeData.address,
          port: nodeData.port,
          api_port: nodeData.api_port ?? null,
          usage_coefficient: nodeData.usage_coefficient,
          connection_type: nodeData.connection_type,
          server_ca: nodeData.server_ca,
          keep_alive: nodeData.keep_alive,
          keep_alive_unit: 'seconds',
          api_key: (nodeData.api_key as string) || '',
          core_config_id: nodeData.core_config_id ?? cores?.[0]?.id,
          data_limit: dataLimitGB,
          data_limit_reset_strategy: nodeData.data_limit_reset_strategy ?? DataLimitResetStrategy.no_reset,
          reset_time: nodeData.reset_time ?? null,
          default_timeout: nodeData.default_timeout ?? 10,
          internal_timeout: nodeData.internal_timeout ?? 15,
          proxy_url: nodeData.proxy_url ?? '',
        })
        lastSyncedNodeRef.current = nodeData
        setIsFetchingNodeData(false)
      } else {
        const fetchNodeData = async () => {
          setIsFetchingNodeData(true)
          try {
            const nodeData = await getNode(editingNodeId)

            const dataLimitBytes = nodeData.data_limit ?? null
            const dataLimitGB = dataLimitBytes !== null && dataLimitBytes !== undefined && dataLimitBytes > 0 ? dataLimitBytes / (1024 * 1024 * 1024) : 0

            form.reset({
              name: nodeData.name,
              address: nodeData.address,
              port: nodeData.port,
              api_port: nodeData.api_port ?? null,
              usage_coefficient: nodeData.usage_coefficient,
              connection_type: nodeData.connection_type,
              server_ca: nodeData.server_ca,
              keep_alive: nodeData.keep_alive,
              keep_alive_unit: 'seconds',
              api_key: (nodeData.api_key as string) || '',
              core_config_id: nodeData.core_config_id ?? cores?.[0]?.id,
              data_limit: dataLimitGB,
              data_limit_reset_strategy: nodeData.data_limit_reset_strategy ?? DataLimitResetStrategy.no_reset,
              reset_time: nodeData.reset_time ?? null,
              default_timeout: nodeData.default_timeout ?? 10,
              internal_timeout: nodeData.internal_timeout ?? 15,
              proxy_url: nodeData.proxy_url ?? '',
            })
            lastSyncedNodeRef.current = nodeData
          } catch (error) {
            console.error('Error fetching node data:', error)
            toast.error(t('nodes.fetchFailed'))
          } finally {
            setIsFetchingNodeData(false)
          }
        }

        fetchNodeData()
      }
    } else {
      form.reset({
        name: '',
        address: '',
        port: 62050,
        api_port: 62051,
        usage_coefficient: 1,
        connection_type: NodeConnectionType.grpc,
        server_ca: '',
        keep_alive: 60,
        keep_alive_unit: 'seconds',
        api_key: '',
        core_config_id: cores?.[0]?.id,
        data_limit: 0,
        data_limit_reset_strategy: DataLimitResetStrategy.no_reset,
        reset_time: -1,
        default_timeout: 10,
        internal_timeout: 15,
        proxy_url: '',
      })
    }
  }, [editingNode, editingNodeId, isDialogOpen, cores, initialNodeData, form])

  useEffect(() => {
    if (isDialogOpen && cores?.[0]?.id) {
      const currentValue = form.getValues('core_config_id')
      if (!currentValue || currentValue < 1) {
        form.setValue('core_config_id', cores[0].id, { shouldValidate: true })
      }
    }
  }, [isDialogOpen, cores, form])

  useEffect(() => {
    if (isDialogOpen) {
      const currentValue = form.getValues('data_limit_reset_strategy')
      if (currentValue === undefined || currentValue === null) {
        form.setValue('data_limit_reset_strategy', DataLimitResetStrategy.no_reset, { shouldValidate: true })
      }
    }
  }, [isDialogOpen, form])

  const checkNodeStatus = async () => {
    const values = form.getValues()

    if (!values.name || !values.address || !values.port) {
      return
    }

    setStatusChecking(true)
    setErrorDetails(null)

    try {
      if (editingNode && editingNodeId) {
        await refetchNode()
      } else {
        setErrorDetails(t('nodeModal.statusMessages.checkUnavailableForNew'))
      }
    } catch (error: any) {
      console.error('Node status check failed:', error)
      setErrorDetails(error?.message || 'Failed to connect to node. Please check your connection settings.')
    } finally {
      setStatusChecking(false)
    }
  }
  useEffect(() => {
    if (currentNode?.status === 'error') {
      setErrorDetails(currentNode.message || 'Node has an error')
    } else if (currentNode?.status) {
      setErrorDetails(null)
    }
  }, [currentNode?.status, currentNode?.message])

  const onSubmit = async (values: NodeFormValues) => {
    try {
      const keepAliveUnit = values.keep_alive_unit ?? 'seconds'
      const keepAliveInSeconds = keepAliveUnit === 'minutes' ? values.keep_alive * 60 : keepAliveUnit === 'hours' ? values.keep_alive * 3600 : values.keep_alive

      const baseData = {
        ...values,
        keep_alive: keepAliveInSeconds,
        keep_alive_unit: undefined,
        data_limit: gbToBytes(values.data_limit),
        reset_time: values.reset_time !== null && values.reset_time !== undefined ? values.reset_time : -1,
        api_port: values.api_port ?? undefined,
        proxy_url: values.proxy_url?.trim() || null,
      }

      let nodeId: number | undefined

      if (editingNode && editingNodeId) {
        const modifyData: typeof baseData & { data_limit_reset_strategy?: DataLimitResetStrategy | null } = {
          ...baseData,
          data_limit_reset_strategy:
            values.data_limit_reset_strategy !== undefined ? (values.data_limit_reset_strategy === null ? DataLimitResetStrategy.no_reset : values.data_limit_reset_strategy) : undefined,
        }
        await modifyNodeMutation.mutateAsync({
          nodeId: editingNodeId,
          data: modifyData,
        })
        nodeId = editingNodeId
        toast.success(
          t('nodes.editSuccess', {
            name: values.name,
            defaultValue: 'Node «{name}» has been updated successfully',
          }),
        )
      } else {
        const createData: typeof baseData & { data_limit_reset_strategy?: DataLimitResetStrategy } = {
          ...baseData,
          data_limit_reset_strategy: values.data_limit_reset_strategy ?? DataLimitResetStrategy.no_reset,
        }
        const result = await addNodeMutation.mutateAsync({
          data: createData,
        })
        nodeId = result?.id
        toast.success(
          t('nodes.createSuccess', {
            name: values.name,
            defaultValue: 'Node «{name}» has been created successfully',
          }),
        )
      }

      if (nodeId && editingNode) {
        queryClient.invalidateQueries({ queryKey: [`/api/node/${nodeId}`] })
        lastSyncedNodeRef.current = null
      }
      queryClient.invalidateQueries({ queryKey: ['/api/nodes'] })
      queryClient.invalidateQueries({ queryKey: ['/api/nodes/simple'] })
      onSuccess?.()
      onOpenChange(false)
      form.reset()
    } catch (error: any) {
      const fields = ['name', 'address', 'port', 'core_config_id', 'api_key', 'keep_alive_unit', 'keep_alive', 'server_ca', 'connection_type', 'proxy_url', '']
      handleError({ error, fields, form, contextKey: 'nodes' })
    }
  }

  const statusKey = currentNode?.status
  const statusConnecting = statusKey === 'connecting' || (statusChecking && !statusKey)
  const statusLabel = statusConnecting
    ? t('nodeModal.status.connecting')
    : statusKey === 'connected'
      ? t('nodeModal.status.connected')
      : statusKey === 'error'
        ? t('nodeModal.status.error')
        : statusKey === 'limited'
          ? t('status.limited', { defaultValue: 'Limited' })
          : t('nodeModal.status.disabled')

  const deckTabs = [
    { id: 'link' as const, label: t('nodeModal.connectionBrief', { defaultValue: 'Link' }), hint: t('nodeModal.connectionHint', { defaultValue: 'Endpoint & core' }), icon: Cable },
    { id: 'trust' as const, label: t('nodeModal.certificate', { defaultValue: 'Trust' }), hint: t('nodeModal.certificateHint', { defaultValue: 'Server CA' }), icon: Shield },
    { id: 'advanced' as const, label: t('settings.notifications.advanced.title', { defaultValue: 'Advanced' }), hint: t('nodeModal.advancedHint', { defaultValue: 'Limits & timeouts' }), icon: Settings },
  ]

  return (
    <Dialog open={isDialogOpen} onOpenChange={onOpenChange}>
      <DialogContent
        className="command-surface flex h-full max-h-[94dvh] max-w-full flex-col gap-0 overflow-hidden border p-0 shadow-[6px_6px_0_hsl(var(--pixel-border))] focus:outline-none sm:max-w-[92vw] lg:h-auto lg:max-w-[1100px]"
        onOpenAutoFocus={e => e.preventDefault()}
      >
        <DialogHeader className="mission-brief relative shrink-0 space-y-0 border-b px-5 py-4 sm:px-6 sm:py-5">
          <div className="mission-brief__index" aria-hidden="true">
            {editingNode ? 'EN' : 'CN'}
          </div>
          <div className="relative z-10 flex flex-wrap items-start justify-between gap-4">
            <div className="min-w-0 space-y-1">
              <DialogTitle className="flex items-center gap-2.5">
                <span className="bg-primary text-primary-foreground flex h-9 w-9 items-center justify-center border border-[hsl(var(--pixel-border))] shadow-[2px_2px_0_hsl(var(--pixel-border))]">
                  {editingNode ? <Pencil className="h-4 w-4" /> : <Server className="h-4 w-4" />}
                </span>
                <span className="font-display text-xl font-bold tracking-tight uppercase sm:text-2xl">{editingNode ? t('editNode.title') : t('nodeModal.title')}</span>
              </DialogTitle>
              <DialogDescription className="font-mono text-[10px] font-bold tracking-[0.16em] uppercase">
                {t('nodeModal.description', { defaultValue: 'Node control deck · link · trust · advanced' })}
              </DialogDescription>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <div
                className={cn(
                  'flex h-10 items-center gap-2 border px-3 font-mono text-[10px] font-bold tracking-[0.12em] uppercase',
                  statusConnecting
                    ? 'border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-400'
                    : statusKey === 'connected'
                      ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400'
                      : statusKey === 'error'
                        ? 'border-destructive/40 bg-destructive/10 text-destructive'
                        : statusKey === 'limited'
                          ? 'border-orange-500/40 bg-orange-500/10 text-orange-700 dark:text-orange-400'
                          : 'border-border bg-muted/40 text-muted-foreground',
                )}
              >
                <span
                  className={cn(
                    'h-2 w-2',
                    statusConnecting
                      ? 'animate-pulse bg-amber-500'
                      : statusKey === 'connected'
                        ? 'bg-emerald-500'
                        : statusKey === 'error'
                          ? 'bg-destructive'
                          : statusKey === 'limited'
                            ? 'bg-orange-500'
                            : 'bg-muted-foreground/50',
                  )}
                  aria-hidden
                />
                {statusLabel}
              </div>
              {statusKey === 'error' && (
                <Button variant="ghost" size="sm" onClick={() => setShowErrorDetails(!showErrorDetails)} className="text-muted-foreground hover:text-foreground h-10 px-2 text-xs">
                  {showErrorDetails ? t('nodeModal.hideDetails') : t('nodeModal.showDetails')}
                </Button>
              )}
              <Button variant="outline" size="sm" onClick={checkNodeStatus} disabled={statusChecking || !form.formState.isValid} className="h-10 gap-1.5 border-2 shadow-[2px_2px_0_hsl(var(--pixel-border))]">
                {statusChecking ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                <span className="text-xs font-bold tracking-wide uppercase">{statusChecking ? t('nodeModal.statusChecking') : t('nodeModal.statusCheck')}</span>
              </Button>
            </div>
          </div>

          {showErrorDetails && statusKey === 'error' && (
            <div
              dir="ltr"
              className="border-destructive/40 bg-destructive/10 text-destructive relative z-10 mt-4 max-h-32 overflow-y-auto border p-3 font-mono text-xs break-words whitespace-pre-wrap"
              style={{ whiteSpace: 'pre-line' }}
            >
              {errorDetails || currentNode?.message}
            </div>
          )}
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="flex min-h-0 flex-1 flex-col">
            <div className={cn('flex min-h-0 flex-1 flex-col overflow-hidden lg:flex-row', isFetchingNodeData && 'pointer-events-none blur-sm')}>
              <nav
                className="border-border bg-card/40 flex shrink-0 gap-1 overflow-x-auto border-b p-2 lg:w-52 lg:flex-col lg:gap-0 lg:overflow-visible lg:border-e lg:border-b-0 lg:p-0"
                aria-label={t('nodeModal.deckNav', { defaultValue: 'Node deck' })}
              >
                {deckTabs.map((tab, i) => {
                  const Icon = tab.icon
                  const isActive = deckTab === tab.id
                  return (
                    <button
                      key={tab.id}
                      type="button"
                      onClick={() => setDeckTab(tab.id)}
                      aria-current={isActive ? 'step' : undefined}
                      className={cn(
                        'flex min-w-36 flex-1 items-center gap-3 border px-3 py-2.5 text-start transition-colors lg:min-w-0 lg:flex-none lg:border-x-0 lg:border-t-0 lg:border-b lg:px-4 lg:py-4',
                        isActive ? 'border-primary/40 bg-primary/10 text-primary lg:border-border' : 'border-transparent text-muted-foreground hover:bg-muted/40 hover:text-foreground lg:border-border',
                      )}
                    >
                      <span
                        className={cn(
                          'flex h-8 w-8 shrink-0 items-center justify-center border font-mono text-[10px] font-bold',
                          isActive ? 'border-primary bg-primary text-primary-foreground shadow-[2px_2px_0_hsl(var(--pixel-border))]' : 'border-border',
                        )}
                        aria-hidden="true"
                      >
                        {String(i + 1).padStart(2, '0')}
                      </span>
                      <span className="min-w-0">
                        <span className="flex items-center gap-1.5 truncate text-xs font-bold">
                          <Icon className="h-3.5 w-3.5 shrink-0 opacity-80" aria-hidden />
                          {tab.label}
                        </span>
                        <span className="mt-0.5 hidden truncate font-mono text-[9px] tracking-[0.12em] uppercase opacity-70 lg:block">{tab.hint}</span>
                      </span>
                      {isActive && <span className="ms-auto hidden h-6 w-0.5 bg-current lg:block" aria-hidden="true" />}
                    </button>
                  )
                })}
                <div className="hidden flex-1 lg:block" aria-hidden="true" />
                <div className="border-border hidden border-t px-4 py-3 lg:block">
                  <p className="text-muted-foreground font-mono text-[9px] font-bold tracking-[0.13em] uppercase">{t('nodeModal.liveEndpoint', { defaultValue: 'Live endpoint' })}</p>
                  <p className="mt-1 truncate text-xs font-bold">{form.watch('name') || '—'}</p>
                  <p dir="ltr" className="text-muted-foreground mt-0.5 font-mono text-[10px] tabular-nums">
                    {(form.watch('address') || '—') + ':' + (form.watch('port') || '—')}
                  </p>
                </div>
              </nav>

              <div className="min-h-0 min-w-0 flex-1 overflow-y-auto px-4 py-4 sm:px-5 sm:py-5">
                <div className={cn('space-y-4', deckTab === 'link' ? 'animate-rise block' : 'hidden')}>
                  <div className="border-border bg-card/40 space-y-1 border p-4">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-primary font-mono text-[10px] font-bold tracking-[0.14em] uppercase">01 / Link</p>
                      <span className="online-beacon" aria-hidden="true" />
                    </div>
                    <p className="text-muted-foreground text-xs">{t('nodeModal.connectionHint', { defaultValue: 'Identity, endpoint, and core binding' })}</p>
                  </div>

                  <div className="border-border bg-card/30 space-y-4 border p-4 sm:p-5">
                  <FormField
                    control={form.control}
                    name="name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('nodeModal.name')}</FormLabel>
                        <FormControl>
                          <Input isError={!!form.formState.errors.name} placeholder={t('nodeModal.namePlaceholder')} {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-[1fr_7.5rem]">
                    <FormField
                      control={form.control}
                      name="address"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>{t('nodeModal.address')}</FormLabel>
                          <FormControl>
                            <Input isError={!!form.formState.errors.address} placeholder={t('nodeModal.addressPlaceholder')} {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="port"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>{t('nodeModal.port')}</FormLabel>
                          <FormControl>
                            <Input
                              isError={!!form.formState.errors.port}
                              type="number"
                              placeholder={t('nodeModal.portPlaceholder')}
                              {...field}
                              onChange={e => field.onChange(parseInt(e.target.value))}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>

                  <FormField
                    control={form.control}
                    name="core_config_id"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>{t('nodeModal.coreConfig')}</FormLabel>
                        <Select onValueChange={value => field.onChange(parseInt(value))} value={field.value ? field.value.toString() : t('nodeModal.selectCoreConfig')} disabled={isLoadingCores}>
                          <FormControl>
                            <SelectTrigger>
                              <SelectValue placeholder={isLoadingCores ? t('loading', { defaultValue: 'Loading...' }) : t('nodeModal.selectCoreConfig')} />
                            </SelectTrigger>
                          </FormControl>
                          <SelectContent>
                            {isLoadingCores ? (
                              <SelectItem value="__loading_cores__" disabled>
                                <span className="flex items-center gap-2">
                                  <Loader2 className="h-3 w-3 animate-spin" />
                                  {t('loading', { defaultValue: 'Loading...' })}
                                </span>
                              </SelectItem>
                            ) : (
                              cores?.map((core: CoreSimple) => (
                                <SelectItem key={core.id} value={core.id.toString()}>
                                  {core.name}
                                </SelectItem>
                              ))
                            )}
                          </SelectContent>
                        </Select>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="api_key"
                    render={({ field }) => {
                      const generateUUID = () => {
                        field.onChange(uuidv4())
                      }
                      return (
                        <FormItem>
                          <FormLabel>{t('nodeModal.apiKey')}</FormLabel>
                          <FormControl>
                            <div className={cn('flex w-full min-w-0 items-center gap-2', dir === 'rtl' && 'flex-row-reverse')}>
                              <Input
                                isError={!!form.formState.errors.api_key}
                                type="text"
                                placeholder={t('nodeModal.apiKeyPlaceholder')}
                                autoComplete="off"
                                className="min-w-0 font-mono text-xs sm:text-sm"
                                {...field}
                                onChange={e => field.onChange(e.target.value)}
                              />
                              <Button type="button" variant="outline" size="icon" onClick={generateUUID} className="h-10 w-10 shrink-0" title={t('nodeModal.generateApiKey', { defaultValue: 'Generate API key' })}>
                                <RefreshCw className="h-3.5 w-3.5" aria-hidden />
                              </Button>
                            </div>
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )
                    }}
                  />
                  </div>
                </div>

                <div className={cn('space-y-4', deckTab === 'advanced' ? 'animate-rise block' : 'hidden')}>
                  <div className="border-border bg-card/40 space-y-1 border p-4">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-primary font-mono text-[10px] font-bold tracking-[0.14em] uppercase">03 / Advanced</p>
                      <span className="online-beacon" aria-hidden="true" />
                    </div>
                    <p className="text-muted-foreground text-xs">{t('nodeModal.advancedHint', { defaultValue: 'Usage limits, keep-alive, and timeouts' })}</p>
                  </div>
                  <div className="border-border bg-card/30 space-y-4 border p-4 sm:p-5">
                        <div className="flex flex-col gap-4">
                          <div className="flex flex-col gap-4 sm:flex-row">
                            <FormField
                              control={form.control}
                              name="usage_coefficient"
                              render={({ field }) => (
                                <FormItem className="flex-1">
                                  <FormLabel>{t('nodeModal.usageRatio')}</FormLabel>
                                  <FormControl>
                                    <Input
                                      isError={!!form.formState.errors.usage_coefficient}
                                      type="number"
                                      step="0.1"
                                      placeholder={t('nodeModal.usageRatioPlaceholder')}
                                      {...field}
                                      onChange={e => field.onChange(parseFloat(e.target.value))}
                                    />
                                  </FormControl>
                                  <FormMessage />
                                </FormItem>
                              )}
                            />
                            <FormField
                              control={form.control}
                              name="api_port"
                              render={({ field }) => (
                                <FormItem className="flex-1">
                                  <FormLabel>{t('nodeModal.apiPort')}</FormLabel>
                                  <FormControl>
                                    <Input
                                      isError={!!form.formState.errors.api_port}
                                      type="number"
                                      placeholder={t('nodeModal.apiPortPlaceholder')}
                                      {...field}
                                      value={field.value ?? ''}
                                      onChange={e => {
                                        const value = e.target.value
                                        if (value === '') {
                                          field.onChange(null)
                                        } else {
                                          const numValue = parseInt(value)
                                          if (!isNaN(numValue) && numValue > 0) {
                                            field.onChange(numValue)
                                          }
                                        }
                                      }}
                                    />
                                  </FormControl>
                                  <FormMessage />
                                </FormItem>
                              )}
                            />
                          </div>

                          <FormField
                            control={form.control}
                            name="connection_type"
                            render={({ field }) => (
                              <FormItem className="w-full">
                                <FormLabel>{t('nodeModal.connectionType')}</FormLabel>
                                <Select onValueChange={field.onChange} defaultValue={field.value}>
                                  <FormControl>
                                    <SelectTrigger>
                                      <SelectValue placeholder="Rest" />
                                    </SelectTrigger>
                                  </FormControl>
                                  <SelectContent>
                                    <SelectItem value={NodeConnectionType.grpc}>gRPC</SelectItem>
                                    <SelectItem value={NodeConnectionType.rest}>Rest</SelectItem>
                                  </SelectContent>
                                </Select>
                                <FormMessage />
                              </FormItem>
                            )}
                          />

                          <FormField
                            control={form.control}
                            name="keep_alive"
                            render={({ field }) => {
                              const [displayValue, setDisplayValue] = useState<string>(field.value?.toString() || '')
                              const [unit, setUnit] = useState<'seconds' | 'minutes' | 'hours'>('seconds')

                              const convertToSeconds = (value: number, fromUnit: 'seconds' | 'minutes' | 'hours') => {
                                switch (fromUnit) {
                                  case 'minutes':
                                    return value * 60
                                  case 'hours':
                                    return value * 3600
                                  default:
                                    return value
                                }
                              }

                              const convertFromSeconds = (seconds: number, toUnit: 'seconds' | 'minutes' | 'hours') => {
                                switch (toUnit) {
                                  case 'minutes':
                                    return Math.floor(seconds / 60)
                                  case 'hours':
                                    return Math.floor(seconds / 3600)
                                  default:
                                    return seconds
                                }
                              }

                              return (
                                <FormItem>
                                  <FormLabel>{t('nodeModal.keepAlive')}</FormLabel>
                                  <div className="flex flex-col gap-1.5">
                                    <p className="text-muted-foreground text-xs">{t('nodeModal.keepAliveDescription')}</p>
                                    <div className="flex flex-col gap-2 sm:flex-row">
                                      <FormControl>
                                        <Input
                                          isError={!!form.formState.errors.keep_alive}
                                          type="number"
                                          value={displayValue ?? ''}
                                          onChange={e => {
                                            const value = e.target.value
                                            setDisplayValue(value)
                                            const numValue = parseInt(value) || 0
                                            field.onChange(convertToSeconds(numValue, unit))
                                          }}
                                        />
                                      </FormControl>
                                      <Select
                                        value={unit}
                                        onValueChange={(value: 'seconds' | 'minutes' | 'hours') => {
                                          setUnit(value)
                                          const currentSeconds = field.value || 0
                                          const newDisplayValue = convertFromSeconds(currentSeconds, value)
                                          setDisplayValue(newDisplayValue.toString())
                                        }}
                                      >
                                        <SelectTrigger className="flex-1">
                                          <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                          <SelectItem value="seconds">{t('nodeModal.seconds')}</SelectItem>
                                          <SelectItem value="minutes">{t('nodeModal.minutes')}</SelectItem>
                                          <SelectItem value="hours">{t('nodeModal.hours')}</SelectItem>
                                        </SelectContent>
                                      </Select>
                                    </div>
                                  </div>
                                  <FormMessage />
                                </FormItem>
                              )
                            }}
                          />

                          <div className="flex flex-col gap-4">
                            <FormField
                              control={form.control}
                              name="data_limit"
                              render={({ field }) => (
                                <FormItem className="relative h-full flex-1">
                                  <FormLabel>{t('nodeModal.dataLimit')}</FormLabel>
                                  <FormControl>
                                    <DecimalInput
                                      isError={!!form.formState.errors.data_limit}
                                      placeholder={t('nodeModal.dataLimitPlaceholder', { defaultValue: 'e.g. 1' })}
                                      value={field.value}
                                      emptyValue={0}
                                      zeroValue={0}
                                      formatDisplayValue={value => String(parseFloat(value.toFixed(9)))}
                                      normalizeDisplayValueOnBlur={value => parseFloat(value.toFixed(9))}
                                      onValueChange={value => field.onChange(value ?? 0)}
                                    />
                                  </FormControl>
                                  {field.value !== null && field.value !== undefined && field.value > 0 && field.value < 1 && (
                                    <p dir="ltr" className={cn('text-muted-foreground absolute top-full right-0 mt-1 w-full text-xs', dir === 'rtl' ? 'text-left' : 'text-end')}>
                                      {formatBytes(Math.round(field.value * 1024 * 1024 * 1024))}
                                    </p>
                                  )}
                                  <FormMessage />
                                </FormItem>
                              )}
                            />

                            {form.watch('data_limit') !== null && form.watch('data_limit') !== undefined && Number(form.watch('data_limit')) > 0 && (
                              <FormField
                                control={form.control}
                                name="data_limit_reset_strategy"
                                render={({ field }) => {
                                  const selectValue = (field.value === null || field.value === undefined || field.value === DataLimitResetStrategy.no_reset ? 'none' : field.value) || 'none'

                                  return (
                                    <FormItem>
                                      <FormLabel>{t('nodeModal.dataLimitResetStrategy')}</FormLabel>
                                      <Select
                                        onValueChange={value => {
                                          field.onChange(value === 'none' ? DataLimitResetStrategy.no_reset : value)
                                        }}
                                        value={selectValue}
                                      >
                                        <FormControl>
                                          <SelectTrigger>
                                            <SelectValue placeholder={t('nodeModal.selectDataLimitResetStrategy')} />
                                          </SelectTrigger>
                                        </FormControl>
                                        <SelectContent>
                                          <SelectItem value="none">{t('nodeModal.noReset')}</SelectItem>
                                          <SelectItem value={DataLimitResetStrategy.day}>{t('nodeModal.day')}</SelectItem>
                                          <SelectItem value={DataLimitResetStrategy.week}>{t('nodeModal.week')}</SelectItem>
                                          <SelectItem value={DataLimitResetStrategy.month}>{t('nodeModal.month')}</SelectItem>
                                          <SelectItem value={DataLimitResetStrategy.year}>{t('nodeModal.year')}</SelectItem>
                                        </SelectContent>
                                      </Select>
                                      <FormMessage />
                                    </FormItem>
                                  )
                                }}
                              />
                            )}

                            <FormField
                              control={form.control}
                              name="reset_time"
                              render={({ field }) => {
                                const resetStrategy = form.watch('data_limit_reset_strategy')

                                const decodeResetTime = (value: number | null | undefined, strategy: string | null | undefined): { day?: number; time: Date | null } => {
                                  if (value === null || value === undefined || value === -1 || !strategy || strategy === DataLimitResetStrategy.no_reset) {
                                    return { time: null }
                                  }

                                  const SECONDS_PER_DAY = 86400
                                  let day: number | undefined
                                  let seconds: number

                                  switch (strategy) {
                                    case DataLimitResetStrategy.day:
                                      seconds = value
                                      break
                                    case DataLimitResetStrategy.week:
                                      day = Math.floor(value / SECONDS_PER_DAY)
                                      seconds = value % SECONDS_PER_DAY
                                      break
                                    case DataLimitResetStrategy.month:
                                      day = Math.floor(value / SECONDS_PER_DAY)
                                      seconds = value % SECONDS_PER_DAY
                                      break
                                    case DataLimitResetStrategy.year:
                                      day = Math.floor(value / SECONDS_PER_DAY)
                                      seconds = value % SECONDS_PER_DAY
                                      break
                                    default:
                                      seconds = value
                                  }

                                  const hours = Math.floor(seconds / 3600)
                                  const minutes = Math.floor((seconds % 3600) / 60)
                                  const date = new Date()
                                  date.setHours(hours, minutes, 0, 0)

                                  return { day, time: date }
                                }

                                const encodeResetTime = (day: number | undefined, time: Date | null, strategy: string | null | undefined): number | null => {
                                  if (!time || !strategy || strategy === DataLimitResetStrategy.no_reset) return -1

                                  const SECONDS_PER_DAY = 86400
                                  const hours = time.getHours()
                                  const minutes = time.getMinutes()
                                  const seconds = hours * 3600 + minutes * 60

                                  switch (strategy) {
                                    case DataLimitResetStrategy.day:
                                      return seconds
                                    case DataLimitResetStrategy.week:
                                      return day !== undefined ? day * SECONDS_PER_DAY + seconds : seconds
                                    case DataLimitResetStrategy.month:
                                      return day !== undefined ? day * SECONDS_PER_DAY + seconds : seconds
                                    case DataLimitResetStrategy.year:
                                      return day !== undefined ? day * SECONDS_PER_DAY + seconds : seconds
                                    default:
                                      return seconds
                                  }
                                }

                                const decoded = decodeResetTime(field.value, resetStrategy)
                                const [useIntervalBased, setUseIntervalBased] = useState(field.value === -1 || field.value === null || field.value === undefined)
                                const [selectedDay, setSelectedDay] = useState<number | undefined>(decoded.day)
                                const [selectedTime, setSelectedTime] = useState<Date | null>(decoded.time)
                                const prevFieldValueRef = React.useRef<number | null | undefined>(field.value)
                                const isUpdatingFromFieldRef = React.useRef(false)
                                const prevStateRef = React.useRef<{ useIntervalBased: boolean; selectedDay?: number; selectedTime?: number; resetStrategy?: string | null }>({
                                  useIntervalBased,
                                  selectedDay,
                                  selectedTime: selectedTime?.getTime(),
                                  resetStrategy: resetStrategy ?? undefined,
                                })

                                useEffect(() => {
                                  if (isUpdatingFromFieldRef.current) {
                                    isUpdatingFromFieldRef.current = false
                                    prevFieldValueRef.current = field.value
                                    return
                                  }

                                  if (prevFieldValueRef.current === field.value && prevStateRef.current.resetStrategy === resetStrategy) {
                                    return
                                  }

                                  prevFieldValueRef.current = field.value
                                  const newDecoded = decodeResetTime(field.value, resetStrategy)
                                  const newUseIntervalBased = field.value === -1 || field.value === null || field.value === undefined

                                  setUseIntervalBased(newUseIntervalBased)
                                  setSelectedDay(newDecoded.day)
                                  setSelectedTime(newDecoded.time)
                                  prevStateRef.current = {
                                    useIntervalBased: newUseIntervalBased,
                                    selectedDay: newDecoded.day,
                                    selectedTime: newDecoded.time?.getTime(),
                                    resetStrategy: resetStrategy ?? undefined,
                                  }
                                }, [field.value, resetStrategy])

                                useEffect(() => {
                                  if (!resetStrategy || resetStrategy === DataLimitResetStrategy.no_reset) {
                                    return
                                  }

                                  const stateChanged =
                                    prevStateRef.current.useIntervalBased !== useIntervalBased ||
                                    prevStateRef.current.selectedDay !== selectedDay ||
                                    prevStateRef.current.selectedTime !== selectedTime?.getTime() ||
                                    prevStateRef.current.resetStrategy !== resetStrategy

                                  if (!stateChanged) {
                                    return
                                  }

                                  prevStateRef.current = { useIntervalBased, selectedDay, selectedTime: selectedTime?.getTime(), resetStrategy }

                                  let newValue: number | null

                                  if (useIntervalBased) {
                                    newValue = -1
                                  } else {
                                    newValue = encodeResetTime(selectedDay, selectedTime, resetStrategy)
                                  }

                                  if (newValue !== null && newValue !== field.value) {
                                    isUpdatingFromFieldRef.current = true
                                    field.onChange(newValue)
                                  }
                                }, [useIntervalBased, selectedDay, selectedTime, resetStrategy, field.value])

                                const getDayOptions = () => {
                                  switch (resetStrategy) {
                                    case DataLimitResetStrategy.week:
                                      return [
                                        { value: 0, label: t('nodeModal.monday', { defaultValue: 'Monday' }) },
                                        { value: 1, label: t('nodeModal.tuesday', { defaultValue: 'Tuesday' }) },
                                        { value: 2, label: t('nodeModal.wednesday', { defaultValue: 'Wednesday' }) },
                                        { value: 3, label: t('nodeModal.thursday', { defaultValue: 'Thursday' }) },
                                        { value: 4, label: t('nodeModal.friday', { defaultValue: 'Friday' }) },
                                        { value: 5, label: t('nodeModal.saturday', { defaultValue: 'Saturday' }) },
                                        { value: 6, label: t('nodeModal.sunday', { defaultValue: 'Sunday' }) },
                                      ]
                                    case DataLimitResetStrategy.month:
                                      return Array.from({ length: 28 }, (_, i) => ({
                                        value: i + 1,
                                        label: String(i + 1),
                                      }))
                                    case DataLimitResetStrategy.year:
                                      return Array.from({ length: 365 }, (_, i) => ({
                                        value: i + 1,
                                        label: `${i + 1}`,
                                      }))
                                    default:
                                      return []
                                  }
                                }

                                const dayOptions = getDayOptions()
                                const dataLimit = form.watch('data_limit')

                                if (!dataLimit || dataLimit === null || dataLimit === undefined || Number(dataLimit) <= 0 || !resetStrategy || resetStrategy === DataLimitResetStrategy.no_reset) {
                                  return <></>
                                }

                                return (
                                  <FormItem>
                                    <div className="space-y-3">
                                      <div className="flex items-center justify-between">
                                        <FormLabel>{t('nodeModal.resetTime')}</FormLabel>
                                        <div className="flex items-center gap-2">
                                          <span className="text-muted-foreground text-xs">
                                            {useIntervalBased ? t('nodeModal.intervalBased', { defaultValue: 'Interval-based' }) : t('nodeModal.absoluteTime', { defaultValue: 'Absolute time' })}
                                          </span>
                                          <Switch
                                            checked={!useIntervalBased}
                                            onCheckedChange={checked => {
                                              const newUseIntervalBased = !checked
                                              setUseIntervalBased(newUseIntervalBased)

                                              if (newUseIntervalBased) {
                                                isUpdatingFromFieldRef.current = true
                                                field.onChange(-1)
                                              } else {
                                                const defaultDay =
                                                  resetStrategy === DataLimitResetStrategy.week
                                                    ? 0
                                                    : resetStrategy === DataLimitResetStrategy.month
                                                      ? 1
                                                      : resetStrategy === DataLimitResetStrategy.year
                                                        ? 1
                                                        : undefined
                                                const defaultTime = new Date()
                                                defaultTime.setHours(0, 0, 0, 0)
                                                setSelectedDay(defaultDay)
                                                setSelectedTime(defaultTime)
                                              }
                                            }}
                                          />
                                        </div>
                                      </div>

                                      {!useIntervalBased && (
                                        <div className="space-y-3">
                                          {dayOptions.length > 0 && (
                                            <Select
                                              value={selectedDay?.toString() || ''}
                                              onValueChange={value => {
                                                setSelectedDay(parseInt(value))
                                              }}
                                            >
                                              <SelectTrigger>
                                                <SelectValue
                                                  placeholder={
                                                    resetStrategy === DataLimitResetStrategy.week
                                                      ? t('nodeModal.selectDayOfWeek', { defaultValue: 'Select day of week' })
                                                      : resetStrategy === DataLimitResetStrategy.month
                                                        ? t('nodeModal.selectDayOfMonth', { defaultValue: 'Select day of month' })
                                                        : t('nodeModal.selectDayOfYear', { defaultValue: 'Select day of year' })
                                                  }
                                                />
                                              </SelectTrigger>
                                              <SelectContent>
                                                {dayOptions.map(option => (
                                                  <SelectItem key={option.value} value={option.value.toString()}>
                                                    {option.label}
                                                  </SelectItem>
                                                ))}
                                              </SelectContent>
                                            </Select>
                                          )}

                                          <Input
                                            type="time"
                                            value={selectedTime ? `${String(selectedTime.getHours()).padStart(2, '0')}:${String(selectedTime.getMinutes()).padStart(2, '0')}` : ''}
                                            onChange={e => {
                                              const [hours, minutes] = e.target.value.split(':')
                                              if (hours && minutes) {
                                                const newTime = new Date()
                                                newTime.setHours(parseInt(hours), parseInt(minutes), 0, 0)
                                                setSelectedTime(newTime)
                                              } else {
                                                setSelectedTime(null)
                                              }
                                            }}
                                            placeholder={t('nodeModal.resetTimePlaceholder', { defaultValue: 'Select time' })}
                                            dir="ltr"
                                          />
                                        </div>
                                      )}

                                      {useIntervalBased && (
                                        <p className="text-muted-foreground text-xs">
                                          {t('nodeModal.intervalBasedDescription', {
                                            defaultValue: 'Reset will occur every period from the last reset time',
                                          })}
                                        </p>
                                      )}
                                    </div>
                                    <FormMessage />
                                  </FormItem>
                                )
                              }}
                            />
                            <div className="flex flex-col gap-2 sm:flex-row">
                              <FormField
                                control={form.control}
                                name="default_timeout"
                                render={({ field }) => (
                                  <FormItem className="flex-1">
                                    <FormLabel>{t('nodeModal.defaultTimeout')}</FormLabel>
                                    <FormControl>
                                      <Input
                                        isError={!!form.formState.errors.default_timeout}
                                        type="number"
                                        step="1"
                                        placeholder={t('nodeModal.defaultTimeoutPlaceholder')}
                                        {...field}
                                        onChange={e => field.onChange(parseInt(e.target.value))}
                                      />
                                    </FormControl>
                                    <FormMessage />
                                  </FormItem>
                                )}
                              />
                              <FormField
                                control={form.control}
                                name="internal_timeout"
                                render={({ field }) => (
                                  <FormItem className="flex-1">
                                    <FormLabel>{t('nodeModal.internalTimeout')}</FormLabel>
                                    <FormControl>
                                      <Input
                                        isError={!!form.formState.errors.internal_timeout}
                                        type="number"
                                        step="1"
                                        placeholder={t('nodeModal.internalTimeoutPlaceholder')}
                                        {...field}
                                        onChange={e => field.onChange(parseInt(e.target.value))}
                                      />
                                    </FormControl>
                                    <FormMessage />
                                  </FormItem>
                                )}
                              />
                            </div>
                            <FormField
                              control={form.control}
                              name="proxy_url"
                              render={({ field }) => (
                                <FormItem>
                                  <FormLabel>{t('settings.webhook.general.proxyUrl')}</FormLabel>
                                  <FormControl>
                                    <Input
                                      isError={!!form.formState.errors.proxy_url}
                                      type="url"
                                      placeholder="socks5://127.0.0.1:1080"
                                      {...field}
                                      value={field.value ?? ''}
                                      className="font-mono text-xs sm:text-sm"
                                    />
                                  </FormControl>
                                  <FormMessage />
                                </FormItem>
                              )}
                            />
                          </div>
                        </div>
                  </div>
                </div>

                <div className={cn('space-y-4', deckTab === 'trust' ? 'animate-rise block' : 'hidden')}>
                  <div className="border-border bg-card/40 space-y-1 border p-4">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-primary font-mono text-[10px] font-bold tracking-[0.14em] uppercase">02 / Trust</p>
                      <span className="online-beacon" aria-hidden="true" />
                    </div>
                    <p className="text-muted-foreground text-xs">{t('nodeModal.certificateHint', { defaultValue: 'Server CA used to trust this node' })}</p>
                  </div>
                <FormField
                  control={form.control}
                  name="server_ca"
                  render={({ field }) => (
                    <FormItem className="border-border bg-card/30 flex min-h-[360px] flex-col border p-4 sm:min-h-[440px] sm:p-5">
                      <div className="mb-3 flex items-start justify-between gap-3">
                        <FormLabel className="flex items-center gap-2 text-sm">
                          <Shield className="text-primary h-4 w-4" />
                          {t('nodeModal.certificate')}
                        </FormLabel>
                      </div>
                      <FormControl>
                        <Textarea
                          dir="ltr"
                          placeholder={t('nodeModal.certificatePlaceholder')}
                          className={cn(
                            'bg-muted/20 min-h-[280px] flex-1 resize-none font-mono text-[11px] leading-relaxed sm:min-h-[360px] sm:text-xs',
                            !!form.formState.errors.server_ca && 'border-destructive',
                          )}
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                </div>
              </div>
            </div>
            <DialogFooter className="shrink-0 gap-2 border-t px-4 py-4 sm:justify-end sm:px-5">
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={addNodeMutation.isPending || modifyNodeMutation.isPending} className="border-2">
                {t('cancel')}
              </Button>
              <LoaderButton
                type="submit"
                disabled={addNodeMutation.isPending || modifyNodeMutation.isPending}
                isLoading={addNodeMutation.isPending || modifyNodeMutation.isPending}
                loadingText={editingNode ? t('modifying') : t('creating')}
                className="shadow-[3px_3px_0_hsl(var(--pixel-border))]"
              >
                {editingNode ? t('modify') : t('create')}
              </LoaderButton>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
