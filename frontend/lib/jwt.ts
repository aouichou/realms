/**
 * JWT Token Utilities
 *
 * Client-side JWT decoding and expiry checking for proactive token refresh
 */

interface JWTPayload {
	sub: string;
	exp: number;
	type: 'access' | 'refresh';
	guest?: boolean;
}

/**
 * Decode JWT token payload (does not verify signature!)
 *
 * Note: This is for client-side token inspection only.
 * Never trust decoded token data for security decisions.
 *
 * @param token - JWT token string
 * @returns Decoded payload or null if invalid
 */
export function decodeJwt(token: string): JWTPayload | null {
	try {
		// JWT format: header.payload.signature
		const parts = token.split('.');
		if (parts.length !== 3) {
			return null;
		}

		// Decode the payload (base64url)
		const payload = parts[1];
		const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
		return JSON.parse(decoded) as JWTPayload;
	} catch (error) {
		if (process.env.NODE_ENV === 'development') {
			console.error('[JWT] Failed to decode token:', error);
		}
		return null;
	}
}

/**
 * Check if JWT token is expired
 *
 * @param token - JWT token string
 * @returns true if token is expired or invalid
 */
export function isTokenExpired(token: string): boolean {
	const payload = decodeJwt(token);

	if (!payload || !payload.exp) {
		return true; // Treat invalid tokens as expired
	}

	// exp is in seconds, Date.now() is in milliseconds
	const expiryTime = payload.exp * 1000;
	const now = Date.now();

	return now >= expiryTime;
}

/**
 * Get token expiry date
 *
 * @param token - JWT token string
 * @returns Expiry date or null if invalid
 */
export function getTokenExpiry(token: string): Date | null {
	const payload = decodeJwt(token);

	if (!payload || !payload.exp) {
		return null;
	}

	return new Date(payload.exp * 1000);
}

/**
 * Get time until token expires (in milliseconds)
 *
 * @param token - JWT token string
 * @returns Milliseconds until expiry, 0 if expired, -1 if invalid
 */
export function getTimeUntilExpiry(token: string): number {
	const expiryDate = getTokenExpiry(token);

	if (!expiryDate) {
		return -1; // Invalid token
	}

	const timeLeft = expiryDate.getTime() - Date.now();
	return Math.max(0, timeLeft);
}

/**
 * Check if token will expire soon (within threshold)
 *
 * @param token - JWT token string
 * @param thresholdMs - Time threshold in milliseconds (default: 5 minutes)
 * @returns true if token will expire within threshold
 */
export function willExpireSoon(token: string, thresholdMs: number = 5 * 60 * 1000): boolean {
	const timeLeft = getTimeUntilExpiry(token);

	if (timeLeft < 0) {
		return false; // Invalid token
	}

	return timeLeft <= thresholdMs;
}

/**
 * Format time remaining until expiry as human-readable string
 *
 * @param token - JWT token string
 * @returns Formatted time string (e.g., "5m 30s") or "expired"
 */
export function formatTimeUntilExpiry(token: string): string {
	const timeLeft = getTimeUntilExpiry(token);

	if (timeLeft < 0) {
		return 'invalid';
	}

	if (timeLeft === 0) {
		return 'expired';
	}

	const seconds = Math.floor(timeLeft / 1000);
	const minutes = Math.floor(seconds / 60);
	const hours = Math.floor(minutes / 60);
	const days = Math.floor(hours / 24);

	if (days > 0) {
		return `${days}d ${hours % 24}h`;
	}
	if (hours > 0) {
		return `${hours}h ${minutes % 60}m`;
	}
	if (minutes > 0) {
		return `${minutes}m ${seconds % 60}s`;
	}
	return `${seconds}s`;
}

/**
 * Extract user ID from token
 *
 * @param token - JWT token string
 * @returns User ID or null if invalid
 */
export function getUserIdFromToken(token: string): string | null {
	const payload = decodeJwt(token);
	return payload?.sub || null;
}

/**
 * Check if token is a guest token
 *
 * @param token - JWT token string
 * @returns true if token is for a guest user
 */
export function isGuestToken(token: string): boolean {
	const payload = decodeJwt(token);
	return payload?.guest === true;
}
