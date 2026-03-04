/**
 * CSRF Token Utilities
 *
 * Handles CSRF token management for API requests.
 * Implements Double Submit Cookie pattern.
 *
 * In cross-subdomain deployments (frontend on realms.example.com,
 * API on api.realms.example.com), document.cookie cannot read cookies
 * set by the API. Instead we capture the token from the X-CSRF-Token
 * response header and store it in memory.
 */

// In-memory store for the CSRF token (survives across requests within
// the same page session; lost on full page reload — re-acquired on
// next auth call that returns an X-CSRF-Token header).
let csrfTokenStore: string | null = null;

/**
 * Get CSRF token — checks in-memory store first, then falls back to cookie.
 *
 * @returns CSRF token string or null if not found
 */
function getCsrfToken(): string | null {
	// Prefer in-memory token (works cross-subdomain)
	if (csrfTokenStore) {
		return csrfTokenStore;
	}

	// Fallback: try reading from same-domain cookie (works in dev / same-origin)
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
 * Store CSRF token from response header.
 *
 * Called after login / register / guest-login to capture the token
 * returned by the server in the X-CSRF-Token response header.
 *
 * @param headers - Response headers from fetch
 */
export function setCsrfTokenFromHeader(headers: Headers): void {
	const csrfToken = headers.get('X-CSRF-Token');

	if (csrfToken) {
		csrfTokenStore = csrfToken;
		if (process.env.NODE_ENV === 'development') {
			console.log('[CSRF] Token captured from response header');
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
 * Clear CSRF token (logout)
 *
 * Server will clear cookie, this is just for client-side state
 */
export function clearCsrfToken(): void {
	csrfTokenStore = null;
	if (process.env.NODE_ENV === 'development') {
		console.log('[CSRF] Token will be cleared by server');
	}
}
