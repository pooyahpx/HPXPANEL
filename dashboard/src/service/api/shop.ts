import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { fetcher } from '@/service/http'

export type ShopOrderStatus = 'pending' | 'approved' | 'rejected' | 'awaiting_payment' | 'expired'
export type ShopOrderKind = 'purchase' | 'renewal'

export interface ShopCard {
  number: string
  holder?: string
}

export interface ShopConfig {
  id: number
  admin_id: number
  enabled: boolean
  card_number?: string | null
  card_holder?: string | null
  card_note?: string | null
  card_photos: string[]
  welcome_note?: string | null
  cards: ShopCard[]
  test_enabled: boolean
  test_data_limit: number
  test_expire_days: number
  test_group_ids: number[]
  custom_enabled: boolean
  custom_price_per_gb: number
  custom_price_per_day: number
  custom_price_per_ip: number
  custom_min_gb: number
  custom_max_gb: number
  custom_min_days: number
  custom_max_days: number
  custom_base_ip: number
  custom_group_ids: number[]
  pay_card_enabled: boolean
  pay_zarinpal_enabled: boolean
  pay_zarinpal_merchant_id?: string | null
  pay_zarinpal_sandbox: boolean
  pay_idpay_enabled: boolean
  pay_idpay_api_key?: string | null
  pay_idpay_sandbox: boolean
  pay_nowpayments_enabled: boolean
  pay_nowpayments_api_key?: string | null
  pay_nowpayments_ipn_secret?: string | null
  pay_paypal_enabled: boolean
  pay_paypal_client_id?: string | null
  pay_paypal_client_secret?: string | null
  pay_paypal_sandbox: boolean
  pay_stripe_enabled: boolean
  pay_stripe_secret_key?: string | null
  pay_stripe_webhook_secret?: string | null
  pay_callback_base_url?: string | null
  pay_fx_toman_per_usd: number
  pay_unpaid_expire_minutes: number
  enabled_gateways: string[]
  created_at?: string | null
}

export interface ShopConfigUpdate {
  enabled?: boolean
  card_note?: string | null
  welcome_note?: string | null
  cards?: ShopCard[]
  test_enabled?: boolean
  test_data_limit?: number
  test_expire_days?: number
  test_group_ids?: number[]
  custom_enabled?: boolean
  custom_price_per_gb?: number
  custom_price_per_day?: number
  custom_price_per_ip?: number
  custom_min_gb?: number
  custom_max_gb?: number
  custom_min_days?: number
  custom_max_days?: number
  custom_base_ip?: number
  custom_group_ids?: number[]
  pay_card_enabled?: boolean
  pay_zarinpal_enabled?: boolean
  pay_zarinpal_merchant_id?: string | null
  pay_zarinpal_sandbox?: boolean
  pay_idpay_enabled?: boolean
  pay_idpay_api_key?: string | null
  pay_idpay_sandbox?: boolean
  pay_nowpayments_enabled?: boolean
  pay_nowpayments_api_key?: string | null
  pay_nowpayments_ipn_secret?: string | null
  pay_paypal_enabled?: boolean
  pay_paypal_client_id?: string | null
  pay_paypal_client_secret?: string | null
  pay_paypal_sandbox?: boolean
  pay_stripe_enabled?: boolean
  pay_stripe_secret_key?: string | null
  pay_stripe_webhook_secret?: string | null
  pay_callback_base_url?: string | null
  pay_fx_toman_per_usd?: number
  pay_unpaid_expire_minutes?: number
}

export interface ShopPlan {
  id: number
  admin_id: number
  name: string
  data_limit: number
  expire_days: number
  price_toman: number
  group_ids: number[]
  ip_limit?: number | null
  hwid_limit?: number | null
  is_active: boolean
  created_at?: string | null
}

export interface ShopPlanCreate {
  name: string
  data_limit?: number
  expire_days?: number
  price_toman?: number
  group_ids: number[]
  ip_limit?: number | null
  hwid_limit?: number | null
  is_active?: boolean
}

export interface ShopPlanUpdate extends Partial<ShopPlanCreate> {}

export interface ShopOrder {
  id: number
  plan_id?: number | null
  admin_id: number
  buyer_telegram_id: number
  buyer_username?: string | null
  status: ShopOrderStatus
  order_kind?: ShopOrderKind
  renew_user_id?: number | null
  renew_username?: string | null
  receipt_file_id?: string | null
  has_receipt?: boolean
  created_user_id?: number | null
  created_username?: string | null
  plan_name?: string | null
  plan_price_toman?: number | null
  requested_username?: string | null
  custom_data_gb?: number | null
  custom_expire_days?: number | null
  custom_ip_limit?: number | null
  quoted_price_toman?: number | null
  is_custom?: boolean
  payment_method?: string | null
  payment_ref?: string | null
  payment_url?: string | null
  payment_paid?: boolean
  note?: string | null
  created_at?: string | null
}

export interface ShopOrderList {
  orders: ShopOrder[]
  total: number
}

export interface ShopStats {
  total_buyers: number
  joined: number
  test_claimed: number
  test_accounts: number
  test_used_bytes: number
  orders_pending: number
  orders_approved: number
  orders_rejected: number
  orders_renewed: number
}

export interface ShopApproveResponse {
  order: ShopOrder
  username: string
  subscription_url?: string | null
}

export interface CreateBudgetLedgerEntry {
  id: number
  admin_id: number
  admin_username?: string | null
  entry_type: string
  amount_toman: number
  balance_after: number
  actor_admin_id?: number | null
  user_id?: number | null
  username?: string | null
  billable_gb?: number
  billable_days?: number
  price_per_gb?: number | null
  price_per_day?: number | null
  pricing_mode?: string | null
  tier_gb?: number | null
  detail?: string | null
  settled_with_owner?: boolean
  settled_at?: string | null
  settled_by_admin_id?: number | null
  created_at?: string | null
}

export interface CreateBudgetLedgerList {
  entries: CreateBudgetLedgerEntry[]
  total: number
}

export interface ShopRevenueLedgerEntry {
  id: number
  admin_id: number
  order_id: number
  entry_type: string
  amount_toman: number
  payment_method: string
  payment_ref?: string | null
  buyer_telegram_id?: number | null
  username?: string | null
  detail?: string | null
  settled_with_owner?: boolean
  settled_at?: string | null
  settled_by_admin_id?: number | null
  created_at?: string | null
}

export interface ShopRevenueGatewayTotal {
  payment_method: string
  orders: number
  amount_toman: number
}

export interface ShopRevenueLedgerList {
  entries: ShopRevenueLedgerEntry[]
  total: number
  by_gateway: ShopRevenueGatewayTotal[]
}

export const shopKeys = {
  all: ['shop'] as const,
  config: ['shop', 'config'] as const,
  stats: ['shop', 'stats'] as const,
  plans: ['shop', 'plans'] as const,
  orders: (filter?: Record<string, unknown>) => ['shop', 'orders', filter] as const,
  accounting: (adminId?: number, settled?: boolean) => ['shop', 'accounting', adminId, settled] as const,
  revenue: (filter?: Record<string, unknown>) => ['shop', 'revenue', filter] as const,
}

export const getShopConfig = () => fetcher<ShopConfig>('/api/shop/config')
export const updateShopConfig = (body: ShopConfigUpdate) =>
  fetcher<ShopConfig>('/api/shop/config', { method: 'PUT', body })
export const getShopStats = () => fetcher<ShopStats>('/api/shop/stats')
export const getShopPlans = () => fetcher<ShopPlan[]>('/api/shop/plans')
export const createShopPlan = (body: ShopPlanCreate) =>
  fetcher<ShopPlan>('/api/shop/plans', { method: 'POST', body })
export const updateShopPlan = (planId: number, body: ShopPlanUpdate) =>
  fetcher<ShopPlan>(`/api/shop/plans/${planId}`, { method: 'PATCH', body })
export const deleteShopPlan = (planId: number) =>
  fetcher<void>(`/api/shop/plans/${planId}`, { method: 'DELETE' })
export const getShopOrders = (params?: {
  status?: ShopOrderStatus
  order_kind?: ShopOrderKind
  payment_method?: string
  payment_paid?: boolean
  offset?: number
  limit?: number
}) => {
  const search = new URLSearchParams()
  if (params?.status) search.set('status', params.status)
  if (params?.order_kind) search.set('order_kind', params.order_kind)
  if (params?.payment_method) search.set('payment_method', params.payment_method)
  if (params?.payment_paid != null) search.set('payment_paid', String(params.payment_paid))
  if (params?.offset != null) search.set('offset', String(params.offset))
  if (params?.limit != null) search.set('limit', String(params.limit))
  const q = search.toString()
  return fetcher<ShopOrderList>(`/api/shop/orders${q ? `?${q}` : ''}`)
}
export const approveShopOrder = (orderId: number) =>
  fetcher<ShopApproveResponse>(`/api/shop/orders/${orderId}/approve`, { method: 'POST' })
export const rejectShopOrder = (orderId: number, note?: string) =>
  fetcher<ShopOrder>(`/api/shop/orders/${orderId}/reject`, { method: 'POST', body: { note } })
export const fetchShopOrderReceiptBlob = async (orderId: number) => {
  const res = await fetch(`/api/shop/orders/${orderId}/receipt`, { credentials: 'include' })
  if (!res.ok) throw new Error('receipt failed')
  return res.blob()
}
export const getShopAccounting = (adminId?: number, settled?: boolean) => {
  const search = new URLSearchParams()
  if (adminId != null) search.set('admin_id', String(adminId))
  if (settled != null) search.set('settled', String(settled))
  const q = search.toString()
  return fetcher<CreateBudgetLedgerList>(`/api/shop/accounting${q ? `?${q}` : ''}`)
}
export const settleShopAccounting = (entryId: number, settled: boolean) =>
  fetcher<CreateBudgetLedgerEntry>(`/api/shop/accounting/${entryId}/settle`, {
    method: 'POST',
    body: { settled },
  })

export const getShopRevenue = (params?: {
  admin_id?: number
  payment_method?: string
  settled?: boolean
  offset?: number
  limit?: number
}) => {
  const search = new URLSearchParams()
  if (params?.admin_id != null) search.set('admin_id', String(params.admin_id))
  if (params?.payment_method) search.set('payment_method', params.payment_method)
  if (params?.settled != null) search.set('settled', String(params.settled))
  if (params?.offset != null) search.set('offset', String(params.offset))
  if (params?.limit != null) search.set('limit', String(params.limit))
  const q = search.toString()
  return fetcher<ShopRevenueLedgerList>(`/api/shop/revenue${q ? `?${q}` : ''}`)
}

export const settleShopRevenue = (entryId: number, settled: boolean) =>
  fetcher<ShopRevenueLedgerEntry>(`/api/shop/revenue/${entryId}/settle`, {
    method: 'POST',
    body: { settled },
  })

export const useShopConfig = (enabled = true) =>
  useQuery({ queryKey: shopKeys.config, queryFn: getShopConfig, enabled, staleTime: 10_000 })
export const useShopStats = (enabled = true) =>
  useQuery({ queryKey: shopKeys.stats, queryFn: getShopStats, enabled, staleTime: 10_000 })
export const useShopPlans = (enabled = true) =>
  useQuery({ queryKey: shopKeys.plans, queryFn: getShopPlans, enabled, staleTime: 10_000 })
export const useShopOrders = (
  filter?: { status?: ShopOrderStatus; order_kind?: ShopOrderKind; payment_method?: string; payment_paid?: boolean },
  enabled = true,
) =>
  useQuery({
    queryKey: shopKeys.orders(filter),
    queryFn: () => getShopOrders(filter),
    enabled,
    staleTime: 5_000,
  })
export const useShopAccounting = (adminId?: number, enabled = true, settled?: boolean) =>
  useQuery({
    queryKey: shopKeys.accounting(adminId, settled),
    queryFn: () => getShopAccounting(adminId, settled),
    enabled,
    staleTime: 10_000,
  })
export const useShopRevenue = (
  filter?: { admin_id?: number; payment_method?: string; settled?: boolean },
  enabled = true,
) =>
  useQuery({
    queryKey: shopKeys.revenue(filter),
    queryFn: () => getShopRevenue(filter),
    enabled,
    staleTime: 10_000,
  })

export function useUpdateShopConfig() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: updateShopConfig,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: shopKeys.config })
      qc.invalidateQueries({ queryKey: shopKeys.stats })
    },
  })
}
export function useCreateShopPlan() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: createShopPlan,
    onSuccess: () => qc.invalidateQueries({ queryKey: shopKeys.plans }),
  })
}
export function useUpdateShopPlan() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ planId, body }: { planId: number; body: ShopPlanUpdate }) => updateShopPlan(planId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: shopKeys.plans }),
  })
}
export function useDeleteShopPlan() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: deleteShopPlan,
    onSuccess: () => qc.invalidateQueries({ queryKey: shopKeys.plans }),
  })
}
export function useApproveShopOrder() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: approveShopOrder,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['shop', 'orders'] })
      qc.invalidateQueries({ queryKey: shopKeys.stats })
    },
  })
}
export function useRejectShopOrder() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ orderId, note }: { orderId: number; note?: string }) => rejectShopOrder(orderId, note),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['shop', 'orders'] })
      qc.invalidateQueries({ queryKey: shopKeys.stats })
    },
  })
}
export function useSettleShopAccounting() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ entryId, settled }: { entryId: number; settled: boolean }) => settleShopAccounting(entryId, settled),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['shop', 'accounting'] }),
  })
}
export function useSettleShopRevenue() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ entryId, settled }: { entryId: number; settled: boolean }) => settleShopRevenue(entryId, settled),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['shop', 'revenue'] }),
  })
}
