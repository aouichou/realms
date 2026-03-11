/** Authentication context and utilities for frontend */
import { API_URL } from './api-client';
import { clearCsrfToken, setCsrfTokenFromHeader } from './csrf';

export interface User {
	id: string;
	username: string;
	email: string | null;
	is_guest: boolean;
	created_at: string;
	last_login: string | null;
}

interface AuthTokens {
	access_token: string;
	refresh_token?: string;
	guest_token?: string;
}

interface AuthState {
	user: User | null;
	isAuthenticated: boolean;
	isGuest: boolean;
	isLoading: boolean;
}

/**
 * Authentication service for managing tokens and user sessions
 */
export const authService = {
	/**
	 * Create a guest account for anonymous play
	 */
	async createGuest(): Promise<{ user: User; tokens: AuthTokens }> {
		const response = await fetch(`${API_URL}/api/v1/auth/guest`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			credentials: 'include', // Send/receive cookies
		});

		if (!response.ok) {
			throw new Error('Failed to create guest account');
		}

		const data = await response.json();

		// Capture CSRF token from response
		setCsrfTokenFromHeader(response.headers);

		// Store guest timing metadata (not secrets - those are in httpOnly cookies)
		localStorage.setItem('guest_created_at', Date.now().toString());

		return {
			user: data.user,
			tokens: {
				access_token: '',  // Tokens in httpOnly cookies
				guest_token: data.guest_token,
			},
		};
	},

	/**
	 * Register a new user account
	 */
	async register(
		email: string,
		username: string,
		password: string
	): Promise<{ user: User; tokens: AuthTokens }> {
		const response = await fetch(`${API_URL}/api/v1/auth/register`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ email, username, password }),
			credentials: 'include', // Send/receive cookies
		});

		if (!response.ok) {
			const error = await response.json();
			throw new Error(error.detail || 'Registration failed');
		}

		const data = await response.json();

		// Capture CSRF token from response headers
		setCsrfTokenFromHeader(response.headers);

		// Clear guest timing data
		localStorage.removeItem('guest_created_at');

		return {
			user: data.user,
			tokens: {
				access_token: '',  // Tokens in httpOnly cookies
				refresh_token: '',
			},
		};
	},

	/**
	 * Login with email and password
	 */
	async login(
		email: string,
		password: string
	): Promise<{ user: User; tokens: AuthTokens }> {
		const response = await fetch(`${API_URL}/api/v1/auth/login`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ email, password }),
			credentials: 'include', // Send/receive cookies
		});

		if (!response.ok) {
			const error = await response.json();
			throw new Error(error.detail || 'Login failed');
		}

		const data = await response.json();

		// Capture CSRF token from response headers
		setCsrfTokenFromHeader(response.headers);

		// Clear guest timing data
		localStorage.removeItem('guest_created_at');

		return {
			user: data.user,
			tokens: {
				access_token: '',  // Tokens in httpOnly cookies
				refresh_token: '',
			},
		};
	},

	/**
	 * Claim a guest account with email and password
	 */
	async claimGuest(
		email: string,
		username: string,
		password: string
	): Promise<{ user: User; tokens: AuthTokens }> {
		// guest_token is sent automatically via httpOnly cookie
		const response = await fetch(`${API_URL}/api/v1/auth/claim-guest`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ email, username, password }),
			credentials: 'include', // Send httpOnly cookies including guest_token
		});

		if (!response.ok) {
			const error = await response.json();
			throw new Error(error.detail || 'Failed to claim account');
		}

		const data = await response.json();

		// Capture CSRF token from response headers
		setCsrfTokenFromHeader(response.headers);

		// Clear guest metadata (tokens now in httpOnly cookies)
		localStorage.removeItem('guest_created_at');

		return {
			user: data.user,
			tokens: {
				access_token: '',  // Tokens in httpOnly cookies
				refresh_token: '',
			},
		};
	},

	/**
	 * Get current user info
	 */
	async getCurrentUser(): Promise<User | null> {
		try {
			const response = await fetch(`${API_URL}/api/v1/auth/me`, {
				credentials: 'include', // Send httpOnly cookies
			});

			if (!response.ok) {
				// Session expired or invalid
				return null;
			}

			return await response.json();
		} catch (error) {
			console.error('Failed to get current user:', error);
			return null;
		}
	},

	/**
	 * Refresh access token using refresh token from httpOnly cookie
	 */
	async refreshToken(): Promise<boolean> {
		try {
			// Backend reads refresh_token from httpOnly cookie
			const response = await fetch(`${API_URL}/api/v1/auth/refresh`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ refresh_token: '' }), // Empty body, cookie used
				credentials: 'include', // Send httpOnly cookies
			});

			if (!response.ok) {
				// Refresh token is invalid or expired
				this.logout();
				return false;
			}

			return true;
		} catch (error) {
			console.error('Failed to refresh token:', error);
			this.logout();
			return false;
		}
	},

	/**
	 * Logout (call backend to clear cookies and clear client data)
	 */
	async logout(): Promise<void> {
		try {
			// Call backend logout endpoint to clear httpOnly cookies
			await fetch(`${API_URL}/api/v1/auth/logout`, {
				method: 'POST',
				credentials: 'include',
			});
		} catch (error) {
			console.error('Logout error:', error);
		}

		// Clear CSRF token (server will clear cookie)
		clearCsrfToken();

		// Clear client-side data
		localStorage.removeItem('guest_created_at');
	},

	/**
	 * Check if user is currently a guest
	 * @deprecated Cannot check httpOnly cookie from JS - use getCurrentUser().is_guest instead
	 */
	isGuest(): boolean {
		// guest_token is now in httpOnly cookie, not accessible from JS
		// Use getCurrentUser() and check user.is_guest instead
		return !!localStorage.getItem('guest_created_at');
	},

	/**
	 * Check if should prompt user to claim account
	 * (after 30 minutes of guest play)
	 */
	shouldPromptClaim(): boolean {
		const guestCreatedAt = localStorage.getItem('guest_created_at');

		if (!guestCreatedAt || !this.isGuest()) {
			return false;
		}

		const minutesPlayed = (Date.now() - parseInt(guestCreatedAt)) / 60000;
		return minutesPlayed >= 30;
	},

	/**
	 * Get authorization header for API requests
	 * @deprecated Tokens now in httpOnly cookies, no header needed
	 */
	getAuthHeader(): HeadersInit {
		// No longer needed - cookies sent automatically
		return {};
	},

	/**
	 * Check if user is authenticated
	 * @deprecated Cannot check from client - use getCurrentUser() instead
	 */
	isAuthenticated(): boolean {
		// Cannot determine from client side with httpOnly cookies
		// Use getCurrentUser() to check server-side auth status
		console.warn('isAuthenticated() deprecated - use getCurrentUser() instead');
		return false;
	},
};
