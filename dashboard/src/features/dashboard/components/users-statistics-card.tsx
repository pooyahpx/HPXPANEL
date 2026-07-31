import { UserStatsBars } from '@/components/ui/statistics-card'
import { SystemUsersStats } from '@/service/api'

const UserStatisticsCard = ({ data }: { data: SystemUsersStats | undefined }) => {
  return <UserStatsBars data={data} className="h-full" showHeader />
}

export default UserStatisticsCard
