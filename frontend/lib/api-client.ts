/**
 * Centralized API client with automatic authentication handling
 */

import { getHeadersWithCsrf } from './csrf';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface FetchOptions extends RequestInit {
	headers?: Record<string, string>;
}

let isRefreshing = false;
let failedQueue: Array<{
	resolve: (value?: any) => void;
	reject: (reason?: any) => void;
}> = [];

const processQueue = (error: any = null) => {
	failedQueue.forEach((promise) => {
		if (error) {
			promise.reject(error);
		} else {
			promise.resolve();
		}
	});
	failedQueue = [];
};

/**
 * Enhanced fetch that automatically sends httpOnly cookies for authentication
 * and handles token refresh on 401 responses
 */
export async function apiFetch(endpoint: string, options: FetchOptions = {}): Promise<Response> {
	const language = localStorage.getItem('dm_language') || 'en';

	// Add CSRF token for state-changing requests
	const method = (options.method || 'GET').toUpperCase();
	const needsCsrf = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method);

	let headers: Record<string, string> = {
		'Content-Type': 'application/json',
		'Accept-Language': language,
		...options.headers,
	};

	// Add CSRF token to headers if needed (except for auth endpoints which generate new tokens)
	if (needsCsrf && !endpoint.includes('/auth/login') && !endpoint.includes('/auth/register') && !endpoint.includes('/auth/guest')) {
		headers = getHeadersWithCsrf(headers);
	}

	const url = endpoint.startsWith('http') ? endpoint : `${API_URL}${endpoint}`;

	// Include credentials to send httpOnly cookies
	const response = await fetch(url, {
		...options,
		headers,
		credentials: 'include',
	});

	// Handle 401 - Unauthorized (token expired)
	if (response.status === 401 && !endpoint.includes('/auth/')) {
		// Avoid infinite loops on auth endpoints
		if (isRefreshing) {
			// If already refreshing, queue this request
			return new Promise((resolve, reject) => {
				failedQueue.push({ resolve, reject });
			}).then(() => {
				// Retry the request after token refresh
				return apiFetch(endpoint, options);
			});
		}

		isRefreshing = true;

		try {
			// Import authService dynamically to avoid circular dependency
			const { authService } = await import('./auth');
			const tokens = await authService.refreshToken();

			if (tokens) {
				// Token refreshed successfully
				processQueue();
				isRefreshing = false;

				// Retry the original request with new token
				return apiFetch(endpoint, options);
			} else {
				// Refresh failed, logout user
				processQueue(new Error('Session expired'));
				isRefreshing = false;

				// Redirect to login if in browser
				if (typeof window !== 'undefined') {
					window.location.href = '/login';
				}

				return response;
			}
		} catch (error) {
			processQueue(error);
			isRefreshing = false;
			throw error;
		}
	}

	// Handle 403 - CSRF validation failed
	if (response.status === 403) {
		const contentType = response.headers.get('content-type');
		if (contentType && contentType.includes('application/json')) {
			const errorData = await response.clone().json();
			if (errorData.error === 'CSRFValidationError') {
				// CSRF token is missing or invalid, refresh page to get new token
				if (typeof window !== 'undefined' && process.env.NODE_ENV === 'production') {
					console.error('CSRF validation failed. Refreshing page to get new token.');
					window.location.reload();
				}
			}
		}
	}

	return response;
}

/**
 * API client with convenience methods
 */
export const apiClient = {
	get: (endpoint: string, options?: FetchOptions) =>
		apiFetch(endpoint, { ...options, method: 'GET' }),

	post: (endpoint: string, data?: any, options?: FetchOptions) =>
		apiFetch(endpoint, {
			...options,
			method: 'POST',
			body: data ? JSON.stringify(data) : undefined,
		}),

	put: (endpoint: string, data?: any, options?: FetchOptions) =>
		apiFetch(endpoint, {
			...options,
			method: 'PUT',
			body: data ? JSON.stringify(data) : undefined,
		}),

	patch: (endpoint: string, data?: any, options?: FetchOptions) =>
		apiFetch(endpoint, {
			...options,
			method: 'PATCH',
			body: data ? JSON.stringify(data) : undefined,
		}),

	delete: (endpoint: string, options?: FetchOptions) =>
		apiFetch(endpoint, { ...options, method: 'DELETE' }),
};

/**
 * Export API_URL for components that need it
 */
export { API_URL };
