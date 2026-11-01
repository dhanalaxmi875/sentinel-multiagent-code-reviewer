import { useQuery } from '@tanstack/react-query';
import type { QueryKey } from '@tanstack/react-query';
import { pollingInterval } from '../utils/filterLogic';

export function usePollingQuery<T>(queryKey: QueryKey, queryFn: () => Promise<T>, getStatus: (data: T) => string) {
  return useQuery({
    queryKey,
    queryFn,
    refetchInterval: (query) => pollingInterval(query.state.data ? getStatus(query.state.data) : undefined),
  });
}
