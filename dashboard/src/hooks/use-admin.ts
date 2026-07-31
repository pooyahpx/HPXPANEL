import { AdminDetails, useGetCurrentAdmin } from '@/service/api'
import { useLoaderData } from 'react-router'

export const useAdmin = () => {
  // Get initial admin data from loader
  const initialAdminData = useLoaderData() as AdminDetails

  // Use React Query's useGetCurrentAdmin with proper configuration
  const {
    data: admin,
    isLoading,
    error,
    refetch,
  } = useGetCurrentAdmin({
    query: {
      initialData: initialAdminData,
      staleTime: 5 * 60 * 1000,
      gcTime: 10 * 60 * 1000,
      refetchOnMount: !initialAdminData,
      retry: 2,
      refetchOnReconnect: 'always',
    },
  })

  const clearAdmin = () => {
    // This would typically invalidate the query cache
    // but since we're using React Query, we can just refetch
    refetch()
  }

  return {
    admin: admin || null,
    isLoading,
    error: error as Error | null,
    clearAdmin,
  }
}
