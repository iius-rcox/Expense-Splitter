import { QueryClient, DefaultOptions } from '@tanstack/react-query';

const queryConfig: DefaultOptions = {
  queries: {
    // Stale time: Data considered fresh for 30 seconds
    staleTime: 30_000,

    // Garbage collection: Remove unused data after 10 minutes
    gcTime: 600_000,

    // Retry logic: Retry failed queries unless 4xx error
    retry: (failureCount, error: any) => {
      // Don't retry 4xx errors (client errors)
      if (error?.response?.status >= 400 && error?.response?.status < 500) {
        return false;
      }
      // Retry up to 3 times for other errors
      return failureCount < 3;
    },

    // Refetch on window focus (disabled by default, enable per-query if needed)
    refetchOnWindowFocus: false,

    // Refetch on reconnect
    refetchOnReconnect: true,

    // Request deduplication
    structuralSharing: true,
  },
  mutations: {
    // Retry mutations once on failure
    retry: 1,
  },
};

export const queryClient = new QueryClient({
  defaultOptions: queryConfig,
});
