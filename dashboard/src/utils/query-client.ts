import { QueryClient } from '@tanstack/react-query'

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
      // Pause interval polling while the tab is backgrounded.
      refetchIntervalInBackground: false,
      staleTime: 10_000,
      gcTime: 5 * 60_000,
      retry: 1,
    },
  },
})
