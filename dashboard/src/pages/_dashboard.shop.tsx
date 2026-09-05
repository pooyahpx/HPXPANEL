import { EmptyState } from '@/components/common/empty-state'
import PageTransition from '@/components/layout/page-transition'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import { useAdmin } from '@/hooks/use-admin'
import useDirDetection from '@/hooks/use-dir-detection'
import { cn } from '@/lib/utils'
import {
  ShopOrderStatus,
  ShopPlan,
  useApproveShopOrder,
  useCreateShopPlan,
  useDeleteShopPlan,
  useRejectShopOrder,
  useShopConfig,
  useShopOrders,
  useShopPlans,
  useShopStats,
  useUpdateShopConfig,
  useUpdateShopPlan,
} from '@/service/api/shop'
import { hasPermission } from '@/utils/rbac'
import { Check, Plus, RefreshCw, ShoppingBag, Trash2, X } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

const GB = 1024 ** 3

const formatBytes = (bytes: number) => {
  if (!bytes) return '∞'
  if (bytes >= GB) return `${(bytes / GB).toFixed(bytes % GB === 0 ? 0 : 1)} GB`
  return `${Math.round(bytes / (1024 ** 2))} MB`
}

const formatPrice = (price: number) => new Intl.NumberFormat(undefined).format(price)

const statusTone = (status: ShopOrderStatus) => {
  switch (status) {
    case 'pending':
      return 'border-amber-500/35 bg-amber-500/10 text-amber-700 dark:text-amber-400'
    case 'approved':
      return 'border-emerald-500/35 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400'
    case 'rejected':
      return 'border-destructive/35 bg-destructive/10 text-destructive'
  }
}

export default function ShopPage() {
  const { t } = useTranslation()
  const dir = useDirDetection()
  const { admin } = useAdmin()
  const canView = hasPermission(admin, 'users', 'read')
  const canManage = hasPermission(admin, 'users', 'create')
  const [orderFilter, setOrderFilter] = useState<ShopOrderStatus | undefined>('pending')
  const [planForm, setPlanForm] = useState({
    name: '',
    price_toman: '100000',
    data_gb: '30',
    expire_days: '30',
  })
  const [welcomeNote, setWelcomeNote] = useState('')
  const [cardNote, setCardNote] = useState('')
  const [cardNumber, setCardNumber] = useState('')
  const [cardHolder, setCardHolder] = useState('')

  const { data: config, isLoading: configLoading, refetch: refetchConfig } = useShopConfig(canView)
  const { data: stats, isLoading: statsLoading, refetch: refetchStats } = useShopStats(canView)
  const { data: plans, isLoading: plansLoading, refetch: refetchPlans } = useShopPlans(canView)
  const { data: ordersData, isLoading: ordersLoading, isFetching, refetch: refetchOrders } = useShopOrders(orderFilter, canView)

  const updateConfig = useUpdateShopConfig()
  const createPlan = useCreateShopPlan()
  const updatePlan = useUpdateShopPlan()
  const deletePlan = useDeleteShopPlan()
  const approveOrder = useApproveShopOrder()
  const rejectOrder = useRejectShopOrder()

  useEffect(() => {
    if (!config) return
    setWelcomeNote(config.welcome_note || '')
    setCardNote(config.card_note || '')
    const primary = config.cards?.[0]
    setCardNumber(primary?.number || config.card_number || '')
    setCardHolder(primary?.holder || config.card_holder || '')
  }, [config])

  const orders = ordersData?.orders ?? []

  const overviewCards = useMemo(
    () => [
      { label: t('shop.pending'), value: stats?.orders_pending ?? 0 },
      { label: t('shop.approved'), value: stats?.orders_approved ?? 0 },
      { label: t('shop.rejected'), value: stats?.orders_rejected ?? 0 },
      { label: t('shop.buyers'), value: stats?.total_buyers ?? 0 },
    ],
    [stats, t],
  )

  const refreshAll = () => {
    refetchConfig()
    refetchStats()
    refetchPlans()
    refetchOrders()
  }

  if (!canView) {
    return (
      <PageTransition isContentTransition className="w-full">
        <EmptyState title={t('shop.denied')} />
      </PageTransition>
    )
  }

  return (
    <PageTransition isContentTransition className="w-full space-y-6">
      <div className={cn('flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between', dir === 'rtl' && 'sm:flex-row-reverse')} dir={dir}>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t('shop.title')}</h1>
          <p className="text-muted-foreground mt-1 text-sm">{t('shop.subtitle')}</p>
        </div>
        <Button variant="outline" size="sm" onClick={refreshAll} disabled={isFetching}>
          <RefreshCw className={cn('size-4', isFetching && 'animate-spin')} />
          {t('shop.refresh')}
        </Button>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {(statsLoading ? [0, 1, 2, 3] : overviewCards).map((item, index) =>
          statsLoading ? (
            <Skeleton key={index} className="h-24 rounded-xl" />
          ) : (
            <Card key={(item as { label: string }).label} className="border-border/70">
              <CardHeader className="pb-2">
                <CardTitle className="text-muted-foreground text-xs font-medium tracking-wide uppercase">{(item as { label: string }).label}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-3xl font-semibold tabular-nums">{(item as { value: number }).value}</div>
              </CardContent>
            </Card>
          ),
        )}
      </div>

      <Tabs defaultValue="orders" className="w-full">
        <TabsList className="grid w-full grid-cols-3 sm:w-auto sm:inline-grid">
          <TabsTrigger value="orders">{t('shop.orders')}</TabsTrigger>
          <TabsTrigger value="plans">{t('shop.plans')}</TabsTrigger>
          <TabsTrigger value="settings">{t('shop.settings')}</TabsTrigger>
        </TabsList>

        <TabsContent value="orders" className="mt-4 space-y-4">
          <div className="flex flex-wrap gap-2">
            {([undefined, 'pending', 'approved', 'rejected'] as const).map(status => (
              <Button
                key={String(status)}
                size="sm"
                variant={orderFilter === status ? 'default' : 'outline'}
                onClick={() => setOrderFilter(status)}
              >
                {status ? t(`shop.status.${status}`) : t('shop.allOrders')}
              </Button>
            ))}
          </div>

          {ordersLoading ? (
            <Skeleton className="h-64 w-full rounded-xl" />
          ) : orders.length === 0 ? (
            <EmptyState icon={ShoppingBag} title={t('shop.emptyOrders')} description={t('shop.emptyOrdersHint')} />
          ) : (
            <Card>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>#</TableHead>
                      <TableHead>{t('shop.buyer')}</TableHead>
                      <TableHead>{t('shop.plan')}</TableHead>
                      <TableHead>{t('shop.statusLabel')}</TableHead>
                      <TableHead>{t('shop.user')}</TableHead>
                      {canManage ? <TableHead className="text-end">{t('shop.actions')}</TableHead> : null}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {orders.map(order => (
                      <TableRow key={order.id}>
                        <TableCell className="font-mono text-xs">{order.id}</TableCell>
                        <TableCell>
                          <div className="font-medium">{order.buyer_username || order.buyer_telegram_id}</div>
                          <div className="text-muted-foreground font-mono text-[11px]">{order.buyer_telegram_id}</div>
                        </TableCell>
                        <TableCell>
                          <div>{order.plan_name || `#${order.plan_id}`}</div>
                          {order.plan_price_toman != null ? (
                            <div className="text-muted-foreground text-xs">{formatPrice(order.plan_price_toman)} {t('shop.toman')}</div>
                          ) : null}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className={cn('capitalize', statusTone(order.status))}>
                            {t(`shop.status.${order.status}`)}
                          </Badge>
                        </TableCell>
                        <TableCell className="font-mono text-xs">{order.created_username || '—'}</TableCell>
                        {canManage ? (
                          <TableCell className="text-end">
                            {order.status === 'pending' ? (
                              <div className="flex justify-end gap-2">
                                <Button
                                  size="sm"
                                  disabled={approveOrder.isPending}
                                  onClick={async () => {
                                    try {
                                      const result = await approveOrder.mutateAsync(order.id)
                                      toast.success(t('shop.approveSuccess', { username: result.username }))
                                    } catch (error: any) {
                                      toast.error(error?.data?.detail || t('shop.actionFailed'))
                                    }
                                  }}
                                >
                                  <Check className="size-4" />
                                  {t('shop.approve')}
                                </Button>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  disabled={rejectOrder.isPending}
                                  onClick={async () => {
                                    try {
                                      await rejectOrder.mutateAsync({ orderId: order.id })
                                      toast.success(t('shop.rejectSuccess'))
                                    } catch (error: any) {
                                      toast.error(error?.data?.detail || t('shop.actionFailed'))
                                    }
                                  }}
                                >
                                  <X className="size-4" />
                                  {t('shop.reject')}
                                </Button>
                              </div>
                            ) : (
                              '—'
                            )}
                          </TableCell>
                        ) : null}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="plans" className="mt-4 space-y-4">
          {canManage ? (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">{t('shop.addPlan')}</CardTitle>
              </CardHeader>
              <CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                <div className="space-y-1.5">
                  <Label>{t('shop.planName')}</Label>
                  <Input value={planForm.name} onChange={e => setPlanForm(prev => ({ ...prev, name: e.target.value }))} />
                </div>
                <div className="space-y-1.5">
                  <Label>{t('shop.price')}</Label>
                  <Input value={planForm.price_toman} onChange={e => setPlanForm(prev => ({ ...prev, price_toman: e.target.value }))} />
                </div>
                <div className="space-y-1.5">
                  <Label>{t('shop.dataGb')}</Label>
                  <Input value={planForm.data_gb} onChange={e => setPlanForm(prev => ({ ...prev, data_gb: e.target.value }))} />
                </div>
                <div className="space-y-1.5">
                  <Label>{t('shop.expireDays')}</Label>
                  <Input value={planForm.expire_days} onChange={e => setPlanForm(prev => ({ ...prev, expire_days: e.target.value }))} />
                </div>
                <div className="flex items-end">
                  <Button
                    className="w-full"
                    disabled={createPlan.isPending || !planForm.name.trim()}
                    onClick={async () => {
                      try {
                        await createPlan.mutateAsync({
                          name: planForm.name.trim(),
                          price_toman: Number(planForm.price_toman) || 0,
                          data_limit: Math.max(0, Math.round(Number(planForm.data_gb) * GB)) || 0,
                          expire_days: Number(planForm.expire_days) || 0,
                        })
                        setPlanForm({ name: '', price_toman: '100000', data_gb: '30', expire_days: '30' })
                        toast.success(t('shop.planCreated'))
                      } catch (error: any) {
                        toast.error(error?.data?.detail || t('shop.actionFailed'))
                      }
                    }}
                  >
                    <Plus className="size-4" />
                    {t('shop.addPlan')}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : null}

          {plansLoading ? (
            <Skeleton className="h-48 w-full rounded-xl" />
          ) : !plans?.length ? (
            <EmptyState title={t('shop.emptyPlans')} description={t('shop.emptyPlansHint')} />
          ) : (
            <Card>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t('shop.planName')}</TableHead>
                      <TableHead>{t('shop.price')}</TableHead>
                      <TableHead>{t('shop.data')}</TableHead>
                      <TableHead>{t('shop.expire')}</TableHead>
                      <TableHead>{t('shop.active')}</TableHead>
                      {canManage ? <TableHead className="text-end">{t('shop.actions')}</TableHead> : null}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {plans.map((plan: ShopPlan) => (
                      <TableRow key={plan.id}>
                        <TableCell className="font-medium">{plan.name}</TableCell>
                        <TableCell>
                          {formatPrice(plan.price_toman)} {t('shop.toman')}
                        </TableCell>
                        <TableCell>{formatBytes(plan.data_limit)}</TableCell>
                        <TableCell>{plan.expire_days ? `${plan.expire_days}d` : '∞'}</TableCell>
                        <TableCell>
                          <Badge variant={plan.is_active ? 'default' : 'secondary'}>{plan.is_active ? t('shop.active') : t('shop.inactive')}</Badge>
                        </TableCell>
                        {canManage ? (
                          <TableCell className="text-end">
                            <div className="flex justify-end gap-2">
                              <Button
                                size="sm"
                                variant="outline"
                                disabled={updatePlan.isPending}
                                onClick={async () => {
                                  try {
                                    await updatePlan.mutateAsync({ planId: plan.id, body: { is_active: !plan.is_active } })
                                  } catch (error: any) {
                                    toast.error(error?.data?.detail || t('shop.actionFailed'))
                                  }
                                }}
                              >
                                {plan.is_active ? t('shop.deactivate') : t('shop.activate')}
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                disabled={deletePlan.isPending}
                                onClick={async () => {
                                  try {
                                    await deletePlan.mutateAsync(plan.id)
                                    toast.success(t('shop.planDeleted'))
                                  } catch (error: any) {
                                    toast.error(error?.data?.detail || t('shop.actionFailed'))
                                  }
                                }}
                              >
                                <Trash2 className="size-4" />
                              </Button>
                            </div>
                          </TableCell>
                        ) : null}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="settings" className="mt-4 space-y-4">
          {configLoading || !config ? (
            <Skeleton className="h-72 w-full rounded-xl" />
          ) : (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">{t('shop.settings')}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-5">
                <div className="flex items-center justify-between gap-4 rounded-lg border p-3">
                  <div>
                    <div className="font-medium">{t('shop.enabled')}</div>
                    <div className="text-muted-foreground text-sm">{t('shop.enabledHint')}</div>
                  </div>
                  <Switch
                    checked={config.enabled}
                    disabled={!canManage || updateConfig.isPending}
                    onCheckedChange={async checked => {
                      try {
                        await updateConfig.mutateAsync({ enabled: checked })
                        toast.success(t('shop.saved'))
                      } catch (error: any) {
                        toast.error(error?.data?.detail || t('shop.actionFailed'))
                      }
                    }}
                  />
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="space-y-1.5">
                    <Label>{t('shop.cardNumber')}</Label>
                    <Input value={cardNumber} disabled={!canManage} onChange={e => setCardNumber(e.target.value)} />
                  </div>
                  <div className="space-y-1.5">
                    <Label>{t('shop.cardHolder')}</Label>
                    <Input value={cardHolder} disabled={!canManage} onChange={e => setCardHolder(e.target.value)} />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <Label>{t('shop.cardNote')}</Label>
                  <Textarea value={cardNote} disabled={!canManage} onChange={e => setCardNote(e.target.value)} rows={3} />
                </div>

                <div className="space-y-1.5">
                  <Label>{t('shop.welcomeNote')}</Label>
                  <Textarea value={welcomeNote} disabled={!canManage} onChange={e => setWelcomeNote(e.target.value)} rows={3} />
                </div>

                {canManage ? (
                  <Button
                    disabled={updateConfig.isPending}
                    onClick={async () => {
                      try {
                        await updateConfig.mutateAsync({
                          welcome_note: welcomeNote,
                          card_note: cardNote,
                          cards: cardNumber.trim() ? [{ number: cardNumber.trim(), holder: cardHolder.trim() }] : [],
                        })
                        toast.success(t('shop.saved'))
                      } catch (error: any) {
                        toast.error(error?.data?.detail || t('shop.actionFailed'))
                      }
                    }}
                  >
                    {t('shop.saveSettings')}
                  </Button>
                ) : null}
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </PageTransition>
  )
}
