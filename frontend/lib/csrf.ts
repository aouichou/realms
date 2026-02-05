/**
 * CSRF Token Utilities
 *
 * Handles CSRF token management for API requests.
 * Implements Double Submit Cookie pattern.
 */

/**
 * Get CSRF token from cookie
 *
 * @returns CSRF token string or null if not found
 */
export function getCsrfToken(): string | null {
	if (typeof document === 'undefined') {
		return null; // SSR
	}

	const name = 'csrf_token=';
	const decodedCookie = decodeURIComponent(document.cookie);
	const cookies = decodedCookie.split(';');

	for (let cookie of cookies) {
		cookie = cookie.trim();
		if (cookie.indexOf(name) === 0) {
			return cookie.substring(name.length);
		}
	}

	return null;
}

/**
 * Set CSRF token from response header
 *
 * Called after login/register to capture initial CSRF token
 *
 * @param headers - Response headers from fetch
 */
export function setCsrfTokenFromHeader(headers: Headers): void {
	const csrfToken = headers.get('X-CSRF-Token');

	if (csrfToken) {
		// Token is already set as cookie by server, no action needed
		// This is just for logging/debugging
		if (process.env.NODE_ENV === 'development') {
			console.log('[CSRF] Token received from server');
		}
	}
}

/**
 * Get headers with CSRF token for API requests
 *
 * @param additionalHeaders - Additional headers to include
 * @returns Headers object with CSRF token
 */
export function getHeadersWithCsrf(additionalHeaders: Record<string, string> = {}): Record<string, string> {
	const csrfToken = getCsrfToken();

	const headers: Record<string, string> = {
		...additionalHeaders,
	};

	if (csrfToken) {
		headers['X-CSRF-Token'] = csrfToken;
	} else if (process.env.NODE_ENV === 'development') {
		console.warn('[CSRF] No CSRF token found in cookies');
	}

	return headers;
}

/**
 * Check if CSRF token exists
 *
 * @returns true if CSRF token is present
 */
export function hasCsrfToken(): boolean {
	return getCsrfToken() !== null;
}

/**
 * Clear CSRF token (logout)
 *
 * Server will clear cookie, this is just for client-side state
 */
export function clearCsrfToken(): void {
	// Token is httpOnly=false but we don't manually manipulate it
	// Server will clear it via Set-Cookie header
	if (process.env.NODE_ENV === 'development') {
		console.log('[CSRF] Token will be cleared by server');
	}
}

/**
 * Handle CSRF error response
 *
 * @param error - Error from API request
 * @returns true if CSRF error was handled
 */
export function handleCsrfError(error: any): boolean {
	if (error?.response?.status === 403 && error?.response?.data?.error === 'CSRFValidationError') {
		if (process.env.NODE_ENV === 'development') {
			console.error('[CSRF] Validation failed:', error.response.data.message);
		}

		// Could trigger a toast notification here
		// or force page refresh to get new token

		return true;
	}

	return false;
}
