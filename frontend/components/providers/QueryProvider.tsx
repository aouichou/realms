"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

export function QueryProvider({ children }: { children: React.ReactNode }) {
	const [queryClient] = useState(
		() =>
			new QueryClient({
				defaultOptions: {
					queries: {
						// Disable automatic refetching on window focus by default
						refetchOnWindowFocus: false,
						// Retry failed requests once
						retry: 1,
						// Keep data in cache for 10 minutes
						gcTime: 10 * 60 * 1000,
					},
				},
			})
	);

	return (
		<QueryClientProvider client={queryClient}>
			{children}
		</QueryClientProvider>
	);
}
