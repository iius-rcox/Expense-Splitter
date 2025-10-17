/**
 * Standardized stale time configurations for React Query.
 *
 * Pattern Reference: PRPs/ai_docs/DATA_FETCHING_ARCHITECTURE.md
 */

export const STALE_TIMES = {
  /** Always fresh - refetch immediately */
  instant: 0,

  /** Real-time data - 3 seconds */
  realtime: 3_000,

  /** Frequently changing data - 5 seconds */
  frequent: 5_000,

  /** Normal data - 30 seconds (default) */
  normal: 30_000,

  /** Rarely changing data - 5 minutes */
  rare: 300_000,

  /** Static data - never stale */
  static: Infinity,
} as const;

/**
 * Special query key for disabled queries.
 *
 * Use when query should not run based on conditional logic.
 * Example: useQuery({ queryKey: enabled ? ['key'] : DISABLED_QUERY_KEY })
 */
export const DISABLED_QUERY_KEY = ['__disabled__'];
