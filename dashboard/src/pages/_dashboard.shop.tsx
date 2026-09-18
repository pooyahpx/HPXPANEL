import { EmptyState } from '@/components/common/empty-state'
import PageHeader from '@/components/layout/page-header'
import PageTransition from '@/components/layout/page-transition'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
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
import { useGetGroupsSimple } from '@/service/api'
import {
  CreateBudgetLedgerEntry,
  ShopOrder,
  ShopOrderStatus,
  ShopPlan,
  fetchShopOrderReceiptBlob,
  useApproveShopOrder,
  useCreateShopPlan,
  useDeleteShopPlan,
  useRejectShopOrder,
  useShopConfig,
  useShopOrders,
  useShopPlans,
  useShopStats,
  useShopAccounting,
  useUpdateShopConfig,
  useUpdateShopPlan,
  useSettleShopAccounting,
} from '@/service/api/shop'
import { hasPermission } from '@/utils/rbac'
import {
  ArrowDownRight,
  ArrowUpRight,
  Check,
  ImageIcon,
  Pencil,
  Plus,
  Receipt,
  RefreshCw,
  ShoppingBag,
  Trash2,
  Wallet,
  X,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'

type PlanFormState = {
  name: string
  price_toman: string
  data_gb: string
  expire_days: string
  group_ids: number[]
  ip_limit: string
  hwid_limit: string
}

const emptyPlanForm = (): PlanFormState => ({
  name: '',
  price_toman: '100000',
  data_gb: '30',
  expire_days: '30',
  group_ids: [],
  ip_limit: '',
  hwid_limit: '',
})

function ShopPlanGroupsPicker({
  selected,
  onChange,
  disabled,
}: {
  selected: number[]
  onChange: (ids: number[]) => void
  disabled?: boolean
}) {
  const { t } = useTranslation()
  const { data: groupsData, isLoading } = useGetGroupsSimple(
    { all: true },
    {
      query: {
        staleTime: 5 * 60 * 1000,
        refetchOnWindowFocus: true,
      },
    },
  )
  const groups = groupsData?.groups || []

  if (isLoading) {
    return <Skeleton className="h-28 w-full rounded-lg" />
  }

  if (!groups.length) {
    return (
      <div className="text-muted-foreground rounded-lg border border-dashed p-3 text-sm">
        {t('shop.noGroups', { defaultValue: 'No groups yet. Create a group first.' })}
      </div>
    )
  }

  return (
    <div className="max-h-40 space-y-2 overflow-y-auto rounded-lg border p-3">
      {groups.map((group: { id: number; name: string }) => {
        const checked = selected.includes(group.id)
        return (
          <label key={group.id} className="flex cursor-pointer items-center gap-2 text-sm">
            <Checkbox
              checked={checked}
              disabled={disabled}
              onCheckedChange={value => {
                const next = value === true ? [...selected, group.id] : selected.filter(id => id !== group.id)
                onChange(next)
              }}
            />
            <span>{group.name}</span>
          </label>
        )
      })}
    </div>
  )
}

const GB = 1024 ** 3

const formatBytes = (bytes: number) => {
  if (!bytes) return '∞'
  if (bytes >= GB) return `${(bytes / GB).toFixed(bytes % GB === 0 ? 0 : 1)} GB`
  return `${Math.round(bytes / 1024 ** 2)} MB`
}

const formatPrice = (price: number) => new Intl.NumberFormat(undefined).format(price)

const formatAccountingDate = (value?: string | null) => {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

const accountingTypeTone = (entryType: string) => {
  const type = entryType.toLowerCase()
  if (type.includes('refund') || type.includes('credit') || type.includes('top')) {
    return 'border-emerald-500/35 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400'
  }
  if (type.includes('charge') || type.includes('debit')) {
    return 'border-rose-500/35 bg-rose-500/10 text-rose-700 dark:text-rose-400'
  }
  return 'border-border/60 bg-muted/40 text-muted-foreground'
}

const summarizeAccounting = (entries: CreateBudgetLedgerEntry[]) => {
  let charged = 0
  let refunded = 0
  let gb = 0
  let days = 0
  for (const entry of entries) {
    const amount = Math.abs(entry.amount_toman || 0)
    const type = (entry.entry_type || '').toLowerCase()
    if (type.includes('refund') || type.includes('credit') || type.includes('top') || entry.amount_toman > 0) {
      refunded += amount
    } else {
      charged += amount
    }
    gb += entry.billable_gb || 0
    days += entry.billable_days || 0
  }
  return { charged, refunded, gb, days, net: charged - refunded, count: entries.length }
}

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

function orderHasReceipt(order: ShopOrder) {
  return Boolean(order.has_receipt ?? order.receipt_file_id)
}

function ReceiptThumb({ orderId, onOpen }: { orderId: number; onOpen: () => void }) {
  const { t } = useTranslation()
  const [url, setUrl] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let revoked: string | null = null
    let cancelled = false
    fetchShopOrderReceiptBlob(orderId)
      .then(blob => {
        if (cancelled) return
        const objectUrl = URL.createObjectURL(blob)
        revoked = objectUrl
        setUrl(objectUrl)
      })
      .catch(() => {
        if (!cancelled) setFailed(true)
      })
    return () => {
      cancelled = true
      if (revoked) URL.revokeObjectURL(revoked)
    }
  }, [orderId])

  if (failed) {
    return <span className="text-muted-foreground text-xs">{t('shop.receiptLoadFailed')}</span>
  }

  if (!url) {
    return <Skeleton className="h-14 w-14 rounded-md" />
  }

  return (
    <button
      type="button"
      onClick={onOpen}
      className="border-border/80 hover:border-primary/50 focus-visible:ring-ring group relative h-14 w-14 overflow-hidden rounded-md border transition-colors focus-visible:ring-2 focus-visible:outline-none"
      title={t('shop.viewReceipt')}
    >
      <img src={url} alt="" className="h-full w-full object-cover" />
      <span className="absolute inset-0 flex items-center justify-center bg-black/0 transition-colors group-hover:bg-black/35">
        <ImageIcon className="size-4 text-white opacity-0 transition-opacity group-hover:opacity-100" />
      </span>
    </button>
  )
}

export default function ShopPage() {
  const { t } = useTranslation()
  const dir = useDirDetection()
  const { admin } = useAdmin()
  const canView = hasPermission(admin, 'users', 'read')
  const canManage = hasPermission(admin, 'users', 'create')
  const isOwner = Boolean(admin?.role?.is_owner)
  const [orderFilter, setOrderFilter] = useState<'all' | ShopOrderStatus | 'renewal'>('pending')
  const [receiptOrder, setReceiptOrder] = useState<ShopOrder | null>(null)
  const [receiptUrl, setReceiptUrl] = useState<string | null>(null)
  const [receiptLoading, setReceiptLoading] = useState(false)
  const [planForm, setPlanForm] = useState<PlanFormState>(emptyPlanForm)
  const [editingPlan, setEditingPlan] = useState<ShopPlan | null>(null)
  const [editForm, setEditForm] = useState<PlanFormState>(emptyPlanForm)
  const [welcomeNote, setWelcomeNote] = useState('')
  const [cardNote, setCardNote] = useState('')
  const [cardNumber, setCardNumber] = useState('')
  const [cardHolder, setCardHolder] = useState('')
  const [customEnabled, setCustomEnabled] = useState(false)
  const [customPricePerGb, setCustomPricePerGb] = useState('5000')
  const [customPricePerDay, setCustomPricePerDay] = useState('2000')
  const [customPricePerIp, setCustomPricePerIp] = useState('10000')
  const [customMinGb, setCustomMinGb] = useState('1')
  const [customMaxGb, setCustomMaxGb] = useState('500')
  const [customMinDays, setCustomMinDays] = useState('1')
  const [customMaxDays, setCustomMaxDays] = useState('365')
  const [customBaseIp, setCustomBaseIp] = useState('1')
  const [customGroupIds, setCustomGroupIds] = useState<number[]>([])
  const [accountingFilter, setAccountingFilter] = useState<'all' | 'charge' | 'credit' | 'unsettled' | 'settled'>('all')

  const { data: groupsSimple } = useGetGroupsSimple({ all: true }, { query: { staleTime: 5 * 60 * 1000, enabled: canView } })
  const groupNameById = useMemo(() => {
    const map = new Map<number, string>()
    for (const group of groupsSimple?.groups || []) {
      map.set(group.id, group.name)
    }
    return map
  }, [groupsSimple])

  const formatPlanGroups = (ids: number[] | undefined) => {
    if (!ids?.length) return t('shop.noGroupsAssigned', { defaultValue: 'No groups' })
    return ids.map(id => groupNameById.get(id) || `#${id}`).join(', ')
  }

  const openEditPlan = (plan: ShopPlan) => {
    setEditingPlan(plan)
    setEditForm({
      name: plan.name,
      price_toman: String(plan.price_toman ?? 0),
      data_gb: String(((plan.data_limit || 0) / GB).toFixed((plan.data_limit || 0) % GB === 0 ? 0 : 1)),
      expire_days: String(plan.expire_days ?? 0),
      group_ids: [...(plan.group_ids || [])],
      ip_limit: plan.ip_limit != null ? String(plan.ip_limit) : '',
      hwid_limit: plan.hwid_limit != null ? String(plan.hwid_limit) : '',
    })
  }

  const ordersQueryFilter =
    orderFilter === 'all'
      ? undefined
      : orderFilter === 'renewal'
        ? { order_kind: 'renewal' as const }
        : { status: orderFilter }

  const { data: config, isLoading: configLoading, refetch: refetchConfig } = useShopConfig(canView)
  const { data: stats, isLoading: statsLoading, refetch: refetchStats } = useShopStats(canView)
  const { data: plans, isLoading: plansLoading, refetch: refetchPlans } = useShopPlans(canView)
  const { data: ordersData, isLoading: ordersLoading, isFetching, refetch: refetchOrders } = useShopOrders(
    ordersQueryFilter,
    canView,
  )
  const accountingSettledParam =
    accountingFilter === 'settled' ? true : accountingFilter === 'unsettled' ? false : undefined
  const { data: accountingData, isLoading: accountingLoading, refetch: refetchAccounting } = useShopAccounting(
    undefined,
    canView,
    accountingSettledParam,
  )

  const updateConfig = useUpdateShopConfig()
  const createPlan = useCreateShopPlan()
  const updatePlan = useUpdateShopPlan()
  const deletePlan = useDeleteShopPlan()
  const approveOrder = useApproveShopOrder()
  const rejectOrder = useRejectShopOrder()
  const settleAccounting = useSettleShopAccounting()

  useEffect(() => {
    if (!config) return
    setWelcomeNote(config.welcome_note || '')
    setCardNote(config.card_note || '')
    const primary = config.cards?.[0]
    setCardNumber(primary?.number || config.card_number || '')
    setCardHolder(primary?.holder || config.card_holder || '')
    setCustomEnabled(Boolean(config.custom_enabled))
    setCustomPricePerGb(String(config.custom_price_per_gb ?? 0))
    setCustomPricePerDay(String(config.custom_price_per_day ?? 0))
    setCustomPricePerIp(String(config.custom_price_per_ip ?? 0))
    setCustomMinGb(String(config.custom_min_gb ?? 1))
    setCustomMaxGb(String(config.custom_max_gb ?? 500))
    setCustomMinDays(String(config.custom_min_days ?? 1))
    setCustomMaxDays(String(config.custom_max_days ?? 365))
    setCustomBaseIp(String(config.custom_base_ip ?? 1))
    setCustomGroupIds([...(config.custom_group_ids || [])])
  }, [config])

  useEffect(() => {
    if (!receiptOrder || !orderHasReceipt(receiptOrder)) {
      setReceiptUrl(null)
      return
    }
    let revoked: string | null = null
    let cancelled = false
    setReceiptLoading(true)
    fetchShopOrderReceiptBlob(receiptOrder.id)
      .then(blob => {
        if (cancelled) return
        const objectUrl = URL.createObjectURL(blob)
        revoked = objectUrl
        setReceiptUrl(objectUrl)
      })
      .catch(() => {
        if (!cancelled) {
          setReceiptUrl(null)
          toast.error(t('shop.receiptLoadFailed'))
        }
      })
      .finally(() => {
        if (!cancelled) setReceiptLoading(false)
      })
    return () => {
      cancelled = true
      if (revoked) URL.revokeObjectURL(revoked)
    }
  }, [receiptOrder, t])

  const orders = ordersData?.orders ?? []

  const overviewCards = useMemo(
    () => [
      { label: t('shop.pending'), value: stats?.orders_pending ?? 0 },
      { label: t('shop.approved'), value: stats?.orders_approved ?? 0 },
      { label: t('shop.renewals', { defaultValue: 'Renewals' }), value: stats?.orders_renewed ?? 0 },
      { label: t('shop.buyers'), value: stats?.total_buyers ?? 0 },
    ],
    [stats, t],
  )

  const accountingEntries = accountingData?.entries ?? []
  const accountingSummary = useMemo(() => summarizeAccounting(accountingEntries), [accountingEntries])
  const filteredAccounting = useMemo(() => {
    if (accountingFilter === 'all' || accountingFilter === 'settled' || accountingFilter === 'unsettled') {
      return accountingEntries
    }
    return accountingEntries.filter(entry => {
      const type = (entry.entry_type || '').toLowerCase()
      const isCredit = type.includes('refund') || type.includes('credit') || type.includes('top') || entry.amount_toman > 0
      return accountingFilter === 'credit' ? isCredit : !isCredit
    })
  }, [accountingEntries, accountingFilter])

  const refreshAll = () => {
    refetchConfig()
    refetchStats()
    refetchPlans()
    refetchOrders()
    refetchAccounting()
  }

  if (!canView) {
    return (
      <PageTransition isContentTransition className="w-full">
        <EmptyState title={t('shop.denied')} />
      </PageTransition>
    )
  }

  return (
    <div className="flex w-full flex-col items-start">
      <div className="animate-fade-in w-full transform-gpu" style={{ animationDuration: '400ms' }}>
        <PageHeader title="shop.title" description="shop.subtitle" index="08" sectorLabel="Commerce deck" />
      </div>

      <PageTransition isContentTransition className="mx-auto w-full max-w-[1680px] space-y-6 px-4 py-5 md:space-y-8 md:px-6 md:py-7">
        <div className={cn('flex flex-wrap items-center justify-between gap-3', dir === 'rtl' && 'flex-row-reverse')} dir={dir}>
          <p className="text-muted-foreground text-sm">{t('shop.ordersBrief')}</p>
          <Button variant="outline" size="sm" onClick={refreshAll} disabled={isFetching}>
            <RefreshCw className={cn('size-4', isFetching && 'animate-spin')} />
            {t('shop.refresh')}
          </Button>
        </div>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {(statsLoading ? [0, 1, 2, 3] : overviewCards).map((item, index) =>
            statsLoading ? (
              <Skeleton key={index} className="h-28 rounded-xl" />
            ) : (
              <Card key={(item as { label: string }).label} className="border-border/60 bg-card/40">
                <CardHeader className="space-y-3 pb-3">
                  <CardTitle className="text-muted-foreground text-[11px] font-medium tracking-[0.12em] uppercase">
                    {(item as { label: string }).label}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-semibold tracking-tight tabular-nums">{(item as { value: number }).value}</div>
                </CardContent>
              </Card>
            ),
          )}
        </div>

        <Tabs defaultValue="orders" className="w-full space-y-5">
          <TabsList className="grid h-auto w-full grid-cols-2 gap-1 p-1 sm:w-auto sm:inline-grid sm:grid-cols-4">
            <TabsTrigger value="orders" className="px-4 py-2.5">
              {t('shop.orders')}
            </TabsTrigger>
            <TabsTrigger value="plans" className="px-4 py-2.5">
              {t('shop.plans')}
            </TabsTrigger>
            <TabsTrigger value="accounting" className="px-4 py-2.5">
              {t('shop.accounting', { defaultValue: 'Accounting' })}
            </TabsTrigger>
            <TabsTrigger value="settings" className="px-4 py-2.5">
              {t('shop.settings')}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="orders" className="mt-0 space-y-5">
            <div className="flex flex-wrap gap-2">
              {([
                ['all', t('shop.allOrders')],
                ['pending', t('shop.status.pending')],
                ['approved', t('shop.status.approved')],
                ['rejected', t('shop.status.rejected')],
                ['renewal', t('shop.renewals', { defaultValue: 'Renewals' })],
              ] as const).map(([key, label]) => (
                <Button
                  key={key}
                  size="sm"
                  variant={orderFilter === key ? 'default' : 'outline'}
                  onClick={() => setOrderFilter(key)}
                >
                  {label}
                </Button>
              ))}
            </div>

            {ordersLoading ? (
              <Skeleton className="h-72 w-full rounded-xl" />
            ) : orders.length === 0 ? (
              <EmptyState icon={ShoppingBag} title={t('shop.emptyOrders')} description={t('shop.emptyOrdersHint')} />
            ) : (
              <Card className="border-border/60 overflow-hidden">
                <CardContent className="p-0">
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow className="hover:bg-transparent">
                          <TableHead className="w-14 px-4 py-3.5">#</TableHead>
                          <TableHead className="min-w-[140px] px-4 py-3.5">{t('shop.buyer')}</TableHead>
                          <TableHead className="min-w-[160px] px-4 py-3.5">{t('shop.plan')}</TableHead>
                          <TableHead className="w-[88px] px-4 py-3.5">{t('shop.receipt')}</TableHead>
                          <TableHead className="w-[110px] px-4 py-3.5">{t('shop.statusLabel')}</TableHead>
                          <TableHead className="w-[100px] px-4 py-3.5">{t('shop.kind', { defaultValue: 'Kind' })}</TableHead>
                          <TableHead className="min-w-[120px] px-4 py-3.5">{t('shop.user')}</TableHead>
                          {canManage ? <TableHead className="px-4 py-3.5 text-end">{t('shop.actions')}</TableHead> : null}
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {orders.map(order => (
                          <TableRow key={order.id} className="align-middle">
                            <TableCell className="px-4 py-4 font-mono text-xs">{order.id}</TableCell>
                            <TableCell className="px-4 py-4">
                              <div className="space-y-1">
                                <div className="font-medium leading-snug">{order.buyer_username || order.buyer_telegram_id}</div>
                                <div className="text-muted-foreground font-mono text-[11px]">{order.buyer_telegram_id}</div>
                              </div>
                            </TableCell>
                            <TableCell className="px-4 py-4">
                              <div className="space-y-1">
                                <div className="leading-snug">
                                  {order.is_custom
                                    ? t('shop.customOrder', { defaultValue: 'Custom' })
                                    : order.plan_name || (order.plan_id ? `#${order.plan_id}` : '—')}
                                </div>
                                <div className="text-muted-foreground text-xs">
                                  {order.quoted_price_toman != null
                                    ? `${formatPrice(order.quoted_price_toman)} ${t('shop.toman')}`
                                    : order.plan_price_toman != null
                                      ? `${formatPrice(order.plan_price_toman)} ${t('shop.toman')}`
                                      : null}
                                  {order.is_custom
                                    ? ` · ${order.custom_data_gb ?? '—'}GB / ${order.custom_expire_days ?? '—'}d / IP ${order.custom_ip_limit ?? '—'}`
                                    : null}
                                  {order.requested_username ? ` · @${order.requested_username}` : null}
                                </div>
                              </div>
                            </TableCell>
                            <TableCell className="px-4 py-4">
                              {orderHasReceipt(order) ? (
                                <ReceiptThumb orderId={order.id} onOpen={() => setReceiptOrder(order)} />
                              ) : (
                                <span className="text-muted-foreground text-xs">{t('shop.noReceipt')}</span>
                              )}
                            </TableCell>
                            <TableCell className="px-4 py-4">
                              <Badge variant="outline" className={cn('capitalize', statusTone(order.status))}>
                                {t(`shop.status.${order.status}`)}
                              </Badge>
                            </TableCell>
                            <TableCell className="px-4 py-4">
                              <Badge
                                variant="secondary"
                                className={cn(
                                  'font-normal',
                                  order.order_kind === 'renewal' &&
                                    'border-sky-500/35 bg-sky-500/10 text-sky-700 dark:text-sky-400',
                                )}
                              >
                                {order.order_kind === 'renewal'
                                  ? t('shop.renewal', { defaultValue: 'Renewal' })
                                  : t('shop.purchase', { defaultValue: 'Purchase' })}
                              </Badge>
                            </TableCell>
                            <TableCell className="px-4 py-4 font-mono text-xs">
                              {order.created_username || order.renew_username || '—'}
                            </TableCell>
                            {canManage ? (
                              <TableCell className="px-4 py-4 text-end">
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
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="plans" className="mt-0 space-y-5">
            {canManage ? (
              <Card className="border-border/60">
                <CardHeader className="pb-4">
                  <CardTitle className="text-base">{t('shop.addPlan')}</CardTitle>
                </CardHeader>
                <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  <div className="space-y-2">
                    <Label>{t('shop.planName')}</Label>
                    <Input value={planForm.name} onChange={e => setPlanForm(prev => ({ ...prev, name: e.target.value }))} />
                  </div>
                  <div className="space-y-2">
                    <Label>{t('shop.price')}</Label>
                    <Input value={planForm.price_toman} onChange={e => setPlanForm(prev => ({ ...prev, price_toman: e.target.value }))} />
                  </div>
                  <div className="space-y-2">
                    <Label>{t('shop.dataGb')}</Label>
                    <Input value={planForm.data_gb} onChange={e => setPlanForm(prev => ({ ...prev, data_gb: e.target.value }))} />
                  </div>
                  <div className="space-y-2">
                    <Label>{t('shop.expireDays')}</Label>
                    <Input value={planForm.expire_days} onChange={e => setPlanForm(prev => ({ ...prev, expire_days: e.target.value }))} />
                  </div>
                  <div className="space-y-2">
                    <Label>{t('shop.ipLimit', { defaultValue: 'IP limit' })}</Label>
                    <Input
                      value={planForm.ip_limit}
                      placeholder="—"
                      onChange={e => setPlanForm(prev => ({ ...prev, ip_limit: e.target.value }))}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>{t('shop.hwidLimit', { defaultValue: 'HWID limit' })}</Label>
                    <Input
                      value={planForm.hwid_limit}
                      placeholder="—"
                      onChange={e => setPlanForm(prev => ({ ...prev, hwid_limit: e.target.value }))}
                    />
                  </div>
                  <div className="space-y-2 sm:col-span-2">
                    <Label>{t('shop.planGroups', { defaultValue: 'Groups' })}</Label>
                    <p className="text-muted-foreground text-xs">
                      {t('shop.planGroupsHint', {
                        defaultValue: 'Users created from this plan get these groups (required for config).',
                      })}
                    </p>
                    <ShopPlanGroupsPicker
                      selected={planForm.group_ids}
                      onChange={group_ids => setPlanForm(prev => ({ ...prev, group_ids }))}
                      disabled={createPlan.isPending}
                    />
                  </div>
                  <div className="flex items-end">
                    <Button
                      className="w-full"
                      disabled={createPlan.isPending || !planForm.name.trim() || planForm.group_ids.length === 0}
                      onClick={async () => {
                        try {
                          await createPlan.mutateAsync({
                            name: planForm.name.trim(),
                            price_toman: Number(planForm.price_toman) || 0,
                            data_limit: Math.max(0, Math.round(Number(planForm.data_gb) * GB)) || 0,
                            expire_days: Number(planForm.expire_days) || 0,
                            group_ids: planForm.group_ids,
                            ip_limit: planForm.ip_limit.trim() ? Number(planForm.ip_limit) : null,
                            hwid_limit: planForm.hwid_limit.trim() ? Number(planForm.hwid_limit) : null,
                          })
                          setPlanForm(emptyPlanForm())
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
              <Card className="border-border/60 overflow-hidden">
                <CardContent className="p-0">
                  <Table>
                    <TableHeader>
                      <TableRow className="hover:bg-transparent">
                        <TableHead className="px-4 py-3.5">{t('shop.planName')}</TableHead>
                        <TableHead className="px-4 py-3.5">{t('shop.price')}</TableHead>
                        <TableHead className="px-4 py-3.5">{t('shop.data')}</TableHead>
                        <TableHead className="px-4 py-3.5">{t('shop.expire')}</TableHead>
                        <TableHead className="px-4 py-3.5">{t('shop.planGroups', { defaultValue: 'Groups' })}</TableHead>
                        <TableHead className="px-4 py-3.5">{t('shop.ipLimit', { defaultValue: 'IP' })}</TableHead>
                        <TableHead className="px-4 py-3.5">{t('shop.active')}</TableHead>
                        {canManage ? <TableHead className="px-4 py-3.5 text-end">{t('shop.actions')}</TableHead> : null}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {plans.map((plan: ShopPlan) => (
                        <TableRow key={plan.id}>
                          <TableCell className="px-4 py-4 font-medium">{plan.name}</TableCell>
                          <TableCell className="px-4 py-4">
                            {formatPrice(plan.price_toman)} {t('shop.toman')}
                          </TableCell>
                          <TableCell className="px-4 py-4">{formatBytes(plan.data_limit)}</TableCell>
                          <TableCell className="px-4 py-4">{plan.expire_days ? `${plan.expire_days}d` : '∞'}</TableCell>
                          <TableCell className="px-4 py-4">
                            <span
                              className={cn(
                                'text-sm',
                                !(plan.group_ids || []).length && 'text-amber-700 dark:text-amber-400',
                              )}
                            >
                              {formatPlanGroups(plan.group_ids)}
                            </span>
                          </TableCell>
                          <TableCell className="px-4 py-4 tabular-nums text-sm">
                            {plan.ip_limit != null ? plan.ip_limit : '—'}
                            {plan.hwid_limit != null ? ` / H${plan.hwid_limit}` : ''}
                          </TableCell>
                          <TableCell className="px-4 py-4">
                            <Badge variant={plan.is_active ? 'default' : 'secondary'}>{plan.is_active ? t('shop.active') : t('shop.inactive')}</Badge>
                          </TableCell>
                          {canManage ? (
                            <TableCell className="px-4 py-4 text-end">
                              <div className="flex justify-end gap-2">
                                <Button size="sm" variant="outline" onClick={() => openEditPlan(plan)}>
                                  <Pencil className="size-3.5" />
                                  {t('shop.editPlan', { defaultValue: 'Edit' })}
                                </Button>
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

            <Dialog
              open={Boolean(editingPlan)}
              onOpenChange={open => {
                if (!open) {
                  setEditingPlan(null)
                  setEditForm(emptyPlanForm())
                }
              }}
            >
              <DialogContent className="sm:max-w-lg">
                <DialogHeader>
                  <DialogTitle>{t('shop.editPlan', { defaultValue: 'Edit plan' })}</DialogTitle>
                </DialogHeader>
                <div className="grid gap-4 py-2 sm:grid-cols-2">
                  <div className="space-y-2 sm:col-span-2">
                    <Label>{t('shop.planName')}</Label>
                    <Input value={editForm.name} onChange={e => setEditForm(prev => ({ ...prev, name: e.target.value }))} />
                  </div>
                  <div className="space-y-2">
                    <Label>{t('shop.price')}</Label>
                    <Input value={editForm.price_toman} onChange={e => setEditForm(prev => ({ ...prev, price_toman: e.target.value }))} />
                  </div>
                  <div className="space-y-2">
                    <Label>{t('shop.dataGb')}</Label>
                    <Input value={editForm.data_gb} onChange={e => setEditForm(prev => ({ ...prev, data_gb: e.target.value }))} />
                  </div>
                  <div className="space-y-2">
                    <Label>{t('shop.expireDays')}</Label>
                    <Input value={editForm.expire_days} onChange={e => setEditForm(prev => ({ ...prev, expire_days: e.target.value }))} />
                  </div>
                  <div className="space-y-2">
                    <Label>{t('shop.ipLimit', { defaultValue: 'IP limit' })}</Label>
                    <Input value={editForm.ip_limit} onChange={e => setEditForm(prev => ({ ...prev, ip_limit: e.target.value }))} />
                  </div>
                  <div className="space-y-2">
                    <Label>{t('shop.hwidLimit', { defaultValue: 'HWID limit' })}</Label>
                    <Input value={editForm.hwid_limit} onChange={e => setEditForm(prev => ({ ...prev, hwid_limit: e.target.value }))} />
                  </div>
                  <div className="space-y-2 sm:col-span-2">
                    <Label>{t('shop.planGroups', { defaultValue: 'Groups' })}</Label>
                    <ShopPlanGroupsPicker
                      selected={editForm.group_ids}
                      onChange={group_ids => setEditForm(prev => ({ ...prev, group_ids }))}
                      disabled={updatePlan.isPending}
                    />
                  </div>
                </div>
                <DialogFooter>
                  <Button
                    variant="outline"
                    onClick={() => {
                      setEditingPlan(null)
                      setEditForm(emptyPlanForm())
                    }}
                  >
                    {t('cancel', { defaultValue: 'Cancel' })}
                  </Button>
                  <Button
                    disabled={
                      updatePlan.isPending || !editingPlan || !editForm.name.trim() || editForm.group_ids.length === 0
                    }
                    onClick={async () => {
                      if (!editingPlan) return
                      try {
                        await updatePlan.mutateAsync({
                          planId: editingPlan.id,
                          body: {
                            name: editForm.name.trim(),
                            price_toman: Number(editForm.price_toman) || 0,
                            data_limit: Math.max(0, Math.round(Number(editForm.data_gb) * GB)) || 0,
                            expire_days: Number(editForm.expire_days) || 0,
                            group_ids: editForm.group_ids,
                            ip_limit: editForm.ip_limit.trim() ? Number(editForm.ip_limit) : null,
                            hwid_limit: editForm.hwid_limit.trim() ? Number(editForm.hwid_limit) : null,
                          },
                        })
                        toast.success(t('shop.planUpdated', { defaultValue: 'Plan updated' }))
                        setEditingPlan(null)
                        setEditForm(emptyPlanForm())
                      } catch (error: any) {
                        toast.error(error?.data?.detail || t('shop.actionFailed'))
                      }
                    }}
                  >
                    {t('shop.savePlan', { defaultValue: 'Save plan' })}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </TabsContent>

          <TabsContent value="accounting" className="mt-0 space-y-5">
            {accountingLoading ? (
              <div className="space-y-4">
                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                  {[0, 1, 2, 3].map(i => (
                    <Skeleton key={i} className="h-28 rounded-xl" />
                  ))}
                </div>
                <Skeleton className="h-72 w-full rounded-xl" />
              </div>
            ) : !(accountingEntries.length) ? (
              <EmptyState
                icon={Wallet}
                title={t('shop.accountingEmpty', { defaultValue: 'No budget transactions yet' })}
                description={t('shop.accountingEmptyHint', {
                  defaultValue: 'Charges appear when budgeted admins create or upgrade users (GB/days).',
                })}
              />
            ) : (
              <>
                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                  <Card className="border-border/60 overflow-hidden bg-gradient-to-br from-rose-500/10 via-card to-card">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                      <CardTitle className="text-muted-foreground text-[11px] font-medium tracking-[0.12em] uppercase">
                        {t('shop.accountingCharged', { defaultValue: 'Charged' })}
                      </CardTitle>
                      <ArrowDownRight className="size-4 text-rose-500" />
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-semibold tracking-tight tabular-nums text-rose-700 dark:text-rose-400">
                        {formatPrice(accountingSummary.charged)}
                      </div>
                      <p className="text-muted-foreground mt-1 text-xs">{t('shop.toman')}</p>
                    </CardContent>
                  </Card>
                  <Card className="border-border/60 overflow-hidden bg-gradient-to-br from-emerald-500/10 via-card to-card">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                      <CardTitle className="text-muted-foreground text-[11px] font-medium tracking-[0.12em] uppercase">
                        {t('shop.accountingCredited', { defaultValue: 'Credited' })}
                      </CardTitle>
                      <ArrowUpRight className="size-4 text-emerald-500" />
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-semibold tracking-tight tabular-nums text-emerald-700 dark:text-emerald-400">
                        {formatPrice(accountingSummary.refunded)}
                      </div>
                      <p className="text-muted-foreground mt-1 text-xs">{t('shop.toman')}</p>
                    </CardContent>
                  </Card>
                  <Card className="border-border/60 overflow-hidden bg-gradient-to-br from-sky-500/10 via-card to-card">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                      <CardTitle className="text-muted-foreground text-[11px] font-medium tracking-[0.12em] uppercase">
                        {t('shop.accountingUsage', { defaultValue: 'GB / Days' })}
                      </CardTitle>
                      <Receipt className="size-4 text-sky-500" />
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-semibold tracking-tight tabular-nums">
                        {formatPrice(accountingSummary.gb)} / {formatPrice(accountingSummary.days)}
                      </div>
                      <p className="text-muted-foreground mt-1 text-xs">
                        {t('shop.accountingLedgerCount', {
                          defaultValue: '{{count}} entries',
                          count: accountingData?.total ?? accountingSummary.count,
                        })}
                      </p>
                    </CardContent>
                  </Card>
                  <Card className="border-border/60 overflow-hidden bg-gradient-to-br from-amber-500/10 via-card to-card">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                      <CardTitle className="text-muted-foreground text-[11px] font-medium tracking-[0.12em] uppercase">
                        {t('shop.accountingNet', { defaultValue: 'Net charged' })}
                      </CardTitle>
                      <Wallet className="size-4 text-amber-500" />
                    </CardHeader>
                    <CardContent>
                      <div className="text-2xl font-semibold tracking-tight tabular-nums">
                        {formatPrice(accountingSummary.net)}
                      </div>
                      <p className="text-muted-foreground mt-1 text-xs">{t('shop.toman')}</p>
                    </CardContent>
                  </Card>
                </div>

                <div className="flex flex-wrap gap-2">
                  {(
                    [
                      ['all', t('shop.allOrders')],
                      ['charge', t('shop.accountingCharged', { defaultValue: 'Charged' })],
                      ['credit', t('shop.accountingCredited', { defaultValue: 'Credited' })],
                      ['unsettled', t('shop.accountingUnsettled', { defaultValue: 'Unsettled' })],
                      ['settled', t('shop.accountingSettled', { defaultValue: 'Settled' })],
                    ] as const
                  ).map(([key, label]) => (
                    <Button
                      key={key}
                      size="sm"
                      variant={accountingFilter === key ? 'default' : 'outline'}
                      onClick={() => setAccountingFilter(key)}
                    >
                      {label}
                    </Button>
                  ))}
                </div>

                <Card className="border-border/60 overflow-hidden shadow-sm">
                  <CardHeader className="border-border/50 border-b bg-muted/20 py-4">
                    <CardTitle className="text-base">
                      {t('shop.accountingLedger', { defaultValue: 'Budget ledger' })}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    <div className="overflow-x-auto">
                      <Table>
                        <TableHeader>
                          <TableRow className="hover:bg-transparent">
                            <TableHead className="w-14 px-4 py-3.5">#</TableHead>
                            <TableHead className="px-4 py-3.5">
                              {t('shop.accountingWhen', { defaultValue: 'When' })}
                            </TableHead>
                            <TableHead className="px-4 py-3.5">
                              {t('shop.accountingAdmin', { defaultValue: 'Admin' })}
                            </TableHead>
                            <TableHead className="px-4 py-3.5">
                              {t('shop.accountingType', { defaultValue: 'Type' })}
                            </TableHead>
                            <TableHead className="px-4 py-3.5">
                              {t('shop.accountingAmount', { defaultValue: 'Amount' })}
                            </TableHead>
                            <TableHead className="px-4 py-3.5">{t('shop.user')}</TableHead>
                            <TableHead className="px-4 py-3.5">
                              {t('shop.accountingUsage', { defaultValue: 'GB / Days' })}
                            </TableHead>
                            <TableHead className="px-4 py-3.5">
                              {t('shop.accountingBalance', { defaultValue: 'Balance after' })}
                            </TableHead>
                            <TableHead className="px-4 py-3.5">
                              {t('shop.accountingSettle', { defaultValue: 'Settled' })}
                            </TableHead>
                            <TableHead className="px-4 py-3.5">
                              {t('shop.accountingDetail', { defaultValue: 'Detail' })}
                            </TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {filteredAccounting.length === 0 ? (
                            <TableRow>
                              <TableCell colSpan={10} className="text-muted-foreground px-4 py-10 text-center text-sm">
                                {t('shop.accountingFilterEmpty', { defaultValue: 'No entries for this filter.' })}
                              </TableCell>
                            </TableRow>
                          ) : (
                            filteredAccounting.map(entry => {
                              const isCredit =
                                (entry.entry_type || '').toLowerCase().includes('refund') ||
                                (entry.entry_type || '').toLowerCase().includes('credit') ||
                                (entry.entry_type || '').toLowerCase().includes('top') ||
                                entry.amount_toman > 0
                              const settled = Boolean(entry.settled_with_owner)
                              return (
                                <TableRow key={entry.id} className="align-middle">
                                  <TableCell className="px-4 py-3.5 font-mono text-xs">{entry.id}</TableCell>
                                  <TableCell className="text-muted-foreground px-4 py-3.5 text-xs whitespace-nowrap">
                                    {formatAccountingDate(entry.created_at)}
                                  </TableCell>
                                  <TableCell className="px-4 py-3.5 font-medium">
                                    {entry.admin_username || entry.admin_id}
                                  </TableCell>
                                  <TableCell className="px-4 py-3.5">
                                    <div className="flex flex-wrap items-center gap-1.5">
                                      <Badge variant="outline" className={cn('font-normal', accountingTypeTone(entry.entry_type))}>
                                        {entry.entry_type}
                                      </Badge>
                                      {entry.pricing_mode ? (
                                        <Badge variant="secondary" className="font-normal">
                                          {entry.pricing_mode}
                                          {entry.tier_gb ? ` · ${entry.tier_gb}GB` : ''}
                                        </Badge>
                                      ) : null}
                                    </div>
                                  </TableCell>
                                  <TableCell
                                    className={cn(
                                      'px-4 py-3.5 tabular-nums font-medium',
                                      isCredit
                                        ? 'text-emerald-700 dark:text-emerald-400'
                                        : 'text-rose-700 dark:text-rose-400',
                                    )}
                                  >
                                    {isCredit ? '+' : '−'}
                                    {formatPrice(Math.abs(entry.amount_toman))} {t('shop.toman')}
                                  </TableCell>
                                  <TableCell className="px-4 py-3.5 font-mono text-xs">{entry.username || '—'}</TableCell>
                                  <TableCell className="px-4 py-3.5 tabular-nums">
                                    <span className="inline-flex items-center gap-1 rounded-md bg-muted/50 px-2 py-1 text-xs">
                                      {entry.billable_gb} GB
                                      <span className="text-muted-foreground">·</span>
                                      {entry.billable_days}d
                                    </span>
                                  </TableCell>
                                  <TableCell className="px-4 py-3.5 tabular-nums font-medium">
                                    {formatPrice(entry.balance_after)}
                                  </TableCell>
                                  <TableCell className="px-4 py-3.5">
                                    <div className="flex items-center gap-2">
                                      <Badge
                                        variant="outline"
                                        className={cn(
                                          'font-normal',
                                          settled
                                            ? 'border-emerald-500/35 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400'
                                            : 'border-amber-500/35 bg-amber-500/10 text-amber-700 dark:text-amber-400',
                                        )}
                                      >
                                        {settled
                                          ? t('shop.accountingSettled', { defaultValue: 'Settled' })
                                          : t('shop.accountingUnsettled', { defaultValue: 'Unsettled' })}
                                      </Badge>
                                      {isOwner ? (
                                        <Switch
                                          checked={settled}
                                          disabled={settleAccounting.isPending}
                                          onCheckedChange={async checked => {
                                            try {
                                              await settleAccounting.mutateAsync({
                                                entryId: entry.id,
                                                settled: checked,
                                              })
                                              toast.success(
                                                checked
                                                  ? t('shop.accountingSettleOn', { defaultValue: 'Marked as settled with owner' })
                                                  : t('shop.accountingSettleOff', { defaultValue: 'Settlement cleared' }),
                                              )
                                            } catch (error: any) {
                                              toast.error(error?.data?.detail || t('shop.actionFailed'))
                                            }
                                          }}
                                        />
                                      ) : null}
                                    </div>
                                  </TableCell>
                                  <TableCell className="text-muted-foreground max-w-[240px] truncate px-4 py-3.5 text-xs" title={entry.detail || undefined}>
                                    {entry.detail || '—'}
                                  </TableCell>
                                </TableRow>
                              )
                            })
                          )}
                        </TableBody>
                      </Table>
                    </div>
                  </CardContent>
                </Card>
              </>
            )}
          </TabsContent>

          <TabsContent value="settings" className="mt-0 space-y-5">
            {configLoading || !config ? (
              <Skeleton className="h-72 w-full rounded-xl" />
            ) : (
              <Card className="border-border/60">
                <CardHeader className="pb-4">
                  <CardTitle className="text-base">{t('shop.settings')}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="flex items-center justify-between gap-4 rounded-lg border p-4">
                    <div className="space-y-1">
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

                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label>{t('shop.cardNumber')}</Label>
                      <Input value={cardNumber} disabled={!canManage} onChange={e => setCardNumber(e.target.value)} />
                    </div>
                    <div className="space-y-2">
                      <Label>{t('shop.cardHolder')}</Label>
                      <Input value={cardHolder} disabled={!canManage} onChange={e => setCardHolder(e.target.value)} />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label>{t('shop.cardNote')}</Label>
                    <Textarea value={cardNote} disabled={!canManage} onChange={e => setCardNote(e.target.value)} rows={3} />
                  </div>

                  <div className="space-y-2">
                    <Label>{t('shop.welcomeNote')}</Label>
                    <Textarea value={welcomeNote} disabled={!canManage} onChange={e => setWelcomeNote(e.target.value)} rows={3} />
                  </div>

                  <div className="space-y-4 rounded-lg border p-4">
                    <div className="flex items-center justify-between gap-4">
                      <div className="space-y-1">
                        <div className="font-medium">
                          {t('shop.customPurchase', { defaultValue: 'Custom purchase' })}
                        </div>
                        <div className="text-muted-foreground text-sm">
                          {t('shop.customPurchaseHint', {
                            defaultValue: 'Buyers pick GB, days, and extra IP slots. Price = units × rates below.',
                          })}
                        </div>
                      </div>
                      <Switch
                        checked={customEnabled}
                        disabled={!canManage}
                        onCheckedChange={setCustomEnabled}
                      />
                    </div>
                    <div className="grid gap-3 sm:grid-cols-3">
                      <div className="space-y-2">
                        <Label>{t('shop.pricePerGb', { defaultValue: 'Price / GB' })}</Label>
                        <Input value={customPricePerGb} disabled={!canManage} onChange={e => setCustomPricePerGb(e.target.value)} />
                      </div>
                      <div className="space-y-2">
                        <Label>{t('shop.pricePerDay', { defaultValue: 'Price / day' })}</Label>
                        <Input value={customPricePerDay} disabled={!canManage} onChange={e => setCustomPricePerDay(e.target.value)} />
                      </div>
                      <div className="space-y-2">
                        <Label>{t('shop.pricePerIp', { defaultValue: 'Price / extra IP' })}</Label>
                        <Input value={customPricePerIp} disabled={!canManage} onChange={e => setCustomPricePerIp(e.target.value)} />
                      </div>
                      <div className="space-y-2">
                        <Label>{t('shop.minGb', { defaultValue: 'Min GB' })}</Label>
                        <Input value={customMinGb} disabled={!canManage} onChange={e => setCustomMinGb(e.target.value)} />
                      </div>
                      <div className="space-y-2">
                        <Label>{t('shop.maxGb', { defaultValue: 'Max GB' })}</Label>
                        <Input value={customMaxGb} disabled={!canManage} onChange={e => setCustomMaxGb(e.target.value)} />
                      </div>
                      <div className="space-y-2">
                        <Label>{t('shop.baseIp', { defaultValue: 'Free base IP' })}</Label>
                        <Input value={customBaseIp} disabled={!canManage} onChange={e => setCustomBaseIp(e.target.value)} />
                      </div>
                      <div className="space-y-2">
                        <Label>{t('shop.minDays', { defaultValue: 'Min days' })}</Label>
                        <Input value={customMinDays} disabled={!canManage} onChange={e => setCustomMinDays(e.target.value)} />
                      </div>
                      <div className="space-y-2">
                        <Label>{t('shop.maxDays', { defaultValue: 'Max days' })}</Label>
                        <Input value={customMaxDays} disabled={!canManage} onChange={e => setCustomMaxDays(e.target.value)} />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label>{t('shop.customGroups', { defaultValue: 'Custom purchase groups' })}</Label>
                      <p className="text-muted-foreground text-xs">
                        {t('shop.customGroupsHint', {
                          defaultValue: 'Required when custom purchase is enabled.',
                        })}
                      </p>
                      <ShopPlanGroupsPicker
                        selected={customGroupIds}
                        onChange={setCustomGroupIds}
                        disabled={!canManage}
                      />
                    </div>
                  </div>

                  {canManage ? (
                    <Button
                      disabled={updateConfig.isPending || (customEnabled && customGroupIds.length === 0)}
                      onClick={async () => {
                        try {
                          await updateConfig.mutateAsync({
                            welcome_note: welcomeNote,
                            card_note: cardNote,
                            cards: cardNumber.trim() ? [{ number: cardNumber.trim(), holder: cardHolder.trim() }] : [],
                            custom_enabled: customEnabled,
                            custom_price_per_gb: Number(customPricePerGb) || 0,
                            custom_price_per_day: Number(customPricePerDay) || 0,
                            custom_price_per_ip: Number(customPricePerIp) || 0,
                            custom_min_gb: Number(customMinGb) || 1,
                            custom_max_gb: Number(customMaxGb) || 500,
                            custom_min_days: Number(customMinDays) || 1,
                            custom_max_days: Number(customMaxDays) || 365,
                            custom_base_ip: Number(customBaseIp) || 1,
                            custom_group_ids: customGroupIds,
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

      <Dialog open={!!receiptOrder} onOpenChange={open => !open && setReceiptOrder(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {t('shop.viewReceipt')}
              {receiptOrder ? ` · #${receiptOrder.id}` : ''}
            </DialogTitle>
          </DialogHeader>
          <div className="bg-muted/30 flex min-h-[280px] items-center justify-center overflow-hidden rounded-lg border p-2">
            {receiptLoading ? (
              <Skeleton className="h-72 w-full rounded-md" />
            ) : receiptUrl ? (
              <img src={receiptUrl} alt={t('shop.receipt')} className="max-h-[70vh] w-full object-contain" />
            ) : (
              <span className="text-muted-foreground text-sm">{t('shop.receiptLoadFailed')}</span>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
