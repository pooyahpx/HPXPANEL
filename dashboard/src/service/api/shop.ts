import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { fetcher } from '@/service/http'

export type ShopOrderStatus = 'pending' | 'approved' | 'rejected'

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
  group_ids?: number[]
  ip_limit?: number | null
  hwid_limit?: number | null
  is_active?: boolean
}

export interface ShopPlanUpdate extends Partial<ShopPlanCreate> {}

export interface ShopOrder {
  id: number
  plan_id: number
  admin_id: number
  buyer_telegram_id: number
  buyer_username?: string | null
  status: ShopOrderStatus
  receipt_file_id?: string | null
  created_user_id?: number | null
  created_username?: string | null
  plan_name?: string | null
  plan_price_toman?: number | null
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
}

export interface ShopApproveResponse {
  order: ShopOrder
  username: string
  subscription_url?: string | null
}

const shopKeys = {
  all: ['shop'] as const,
  config: ['shop', 'config'] as const,
  stats: ['shop', 'stats'] as const,
  plans: ['shop', 'plans'] as const,
  orders: (status?: ShopOrderStatus | 'all') => ['shop', 'orders', status ?? 'all'] as const,
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

export const getShopOrders = (params?: { status?: ShopOrderStatus; offset?: number; limit?: number }) =>
  fetcher<ShopOrderList>('/api/shop/orders', { params })

export const approveShopOrder = (orderId: number) =>
  fetcher<ShopApproveResponse>(`/api/shop/orders/${orderId}/approve`, { method: 'POST' })

export const rejectShopOrder = (orderId: number, note?: string) =>
  fetcher<ShopOrder>(`/api/shop/orders/${orderId}/reject`, { method: 'POST', body: note ? { note } : {} })

export const useShopConfig = (enabled = true) =>
  useQuery({ queryKey: shopKeys.config, queryFn: getShopConfig, enabled, staleTime: 10_000 })

export const useShopStats = (enabled = true) =>
  useQuery({ queryKey: shopKeys.stats, queryFn: getShopStats, enabled, refetchInterval: 20_000, staleTime: 5_000 })

export const useShopPlans = (enabled = true) =>
  useQuery({ queryKey: shopKeys.plans, queryFn: getShopPlans, enabled, staleTime: 10_000 })

export const useShopOrders = (status?: ShopOrderStatus, enabled = true) =>
  useQuery({
    queryKey: shopKeys.orders(status),
    queryFn: () => getShopOrders({ status, limit: 100 }),
    enabled,
    refetchInterval: 15_000,
    staleTime: 5_000,
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
      qc.invalidateQueries({ queryKey: shopKeys.all })
    },
  })
}

export function useRejectShopOrder() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ orderId, note }: { orderId: number; note?: string }) => rejectShopOrder(orderId, note),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: shopKeys.all })
    },
  })
}
