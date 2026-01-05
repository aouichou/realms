// Performance utilities for React components

import { useEffect, useRef } from 'react';

/**
 * Hook to debounce a value
 * Useful for search inputs and API calls
 */
export function useDebounce<T>(value: T, delay: number): T {
	const [debouncedValue, setDebouncedValue] = useState<T>(value);

	useEffect(() => {
		const handler = setTimeout(() => {
			setDebouncedValue(value);
		}, delay);

		return () => {
			clearTimeout(handler);
		};
	}, [value, delay]);

	return debouncedValue;
}

/**
 * Hook to throttle a function
 * Useful for scroll handlers and frequent events
 */
export function useThrottle<T extends (...args: any[]) => any>(
	callback: T,
	delay: number
): T {
	const lastRan = useRef(Date.now());

	return ((...args) => {
		const now = Date.now();
		if (now - lastRan.current >= delay) {
			callback(...args);
			lastRan.current = now;
		}
	}) as T;
}

/**
 * Hook to track component mount status
 * Prevents state updates on unmounted components
 */
export function useIsMounted(): () => boolean {
	const isMounted = useRef(false);

	useEffect(() => {
		isMounted.current = true;
		return () => {
			isMounted.current = false;
		};
	}, []);

	return () => isMounted.current;
}

/**
 * Hook to lazy load images
 * Improves initial page load time
 */
export function useLazyLoad(ref: React.RefObject<HTMLElement>) {
	useEffect(() => {
		if (!ref.current) return;

		const observer = new IntersectionObserver(
			(entries) => {
				entries.forEach((entry) => {
					if (entry.isIntersecting) {
						const img = entry.target as HTMLImageElement;
						if (img.dataset.src) {
							img.src = img.dataset.src;
							observer.unobserve(img);
						}
					}
				});
			},
			{ rootMargin: '50px' }
		);

		observer.observe(ref.current);

		return () => {
			if (ref.current) {
				observer.unobserve(ref.current);
			}
		};
	}, [ref]);
}

import { useState } from 'react';
