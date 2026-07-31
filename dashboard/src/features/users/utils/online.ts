import dayjs from '@/lib/dayjs'
import { dateUtils } from '@/utils/dateFormatter'

export const ONLINE_THRESHOLD_SECONDS = 60

export const isUserOnline = (lastOnline?: string | null) => {
  if (!lastOnline) return false
  return dayjs().diff(dateUtils.toDayjs(lastOnline), 'seconds') <= ONLINE_THRESHOLD_SECONDS
}
