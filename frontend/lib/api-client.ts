/**
 * Centralized API client with automatic authentication handling
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface FetchOptions extends RequestInit {
	headers?: Record<string, string>;
}

/**
 * Enhanced fetch that automatically includes JWT token from localStorage
 */
export async function apiFetch(endpoint: string, options: FetchOptions = {}): Promise<Response> {
	const token = localStorage.getItem('access_token');
	const language = localStorage.getItem('dm_language') || 'en';

	const headers: Record<string, string> = {
		'Content-Type': 'application/json',
		'Accept-Language': language,
		...options.headers,
	};

	if (token) {
		headers['Authorization'] = `Bearer ${token}`;
	}

	const url = endpoint.startsWith('http') ? endpoint : `${API_URL}${endpoint}`;

	return fetch(url, {
		...options,
		headers,
	});
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
