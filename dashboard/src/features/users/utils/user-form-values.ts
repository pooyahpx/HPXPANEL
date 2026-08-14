import { type UseEditFormValues } from '@/features/users/forms/user-form'
import { type UserResponse } from '@/service/api'
import { bytesToFormGigabytes } from '@/utils/formatByte'
import { normalizeDatePickerValueForEditForm } from '@/utils/userEditDateUtils'

export function buildGroupQuotaGbFromUser(user: UserResponse | null | undefined): Record<number, number> {
  return Object.fromEntries(
    (user?.group_quotas || [])
      .filter(q => q.data_limit != null && Number(q.data_limit) > 0)
      .map(q => [q.group_id, bytesToFormGigabytes(Number(q.data_limit))]),
  )
}

export function buildUserEditFormValues(user: UserResponse): UseEditFormValues {
  return {
    username: user.username,
    status: user.status === 'active' || user.status === 'on_hold' || user.status === 'disabled' ? user.status : 'active',
    data_limit: user.data_limit ? bytesToFormGigabytes(Number(user.data_limit)) : 0,
    hwid_limit: user.hwid_limit ?? null,
    ip_limit: user.ip_limit ?? null,
    expire: normalizeDatePickerValueForEditForm(user.expire),
    note: user.note || '',
    data_limit_reset_strategy: user.data_limit_reset_strategy || undefined,
    group_ids: user.group_ids || [],
    group_quota_gb: buildGroupQuotaGbFromUser(user),
    on_hold_expire_duration: user.on_hold_expire_duration || undefined,
    on_hold_timeout: normalizeDatePickerValueForEditForm(user.on_hold_timeout),
    proxy_settings: user.proxy_settings || undefined,
    next_plan: user.next_plan
      ? {
          user_template_id: user.next_plan.user_template_id ? Number(user.next_plan.user_template_id) : undefined,
          data_limit: user.next_plan.data_limit ? Math.round(Number(user.next_plan.data_limit)) : 0,
          expire: user.next_plan.expire ? Math.round(Number(user.next_plan.expire)) : 0,
          add_remaining_traffic: user.next_plan.add_remaining_traffic || false,
        }
      : undefined,
  }
}
