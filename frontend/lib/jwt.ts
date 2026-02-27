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
function decodeJwt(token: string): JWTPayload | null {
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
 * Get token expiry date
 *
 * @param token - JWT token string
 * @returns Expiry date or null if invalid
 */
function getTokenExpiry(token: string): Date | null {
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
function getTimeUntilExpiry(token: string): number {
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

