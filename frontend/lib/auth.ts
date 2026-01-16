/** Authentication context and utilities for frontend */
import { API_URL } from './api-client';

export interface User {
	id: string;
	username: string;
	email: string | null;
	is_guest: boolean;
	created_at: string;
	last_login: string | null;
}

export interface AuthTokens {
	access_token: string;
	refresh_token?: string;
	guest_token?: string;
}

export interface AuthState {
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
		});

		if (!response.ok) {
			throw new Error('Failed to create guest account');
		}

		const data = await response.json();

		// Store tokens in localStorage
		localStorage.setItem('access_token', data.access_token);
		if (data.guest_token) {
			localStorage.setItem('guest_token', data.guest_token);
			localStorage.setItem('guest_created_at', Date.now().toString());
		}

		return {
			user: data.user,
			tokens: {
				access_token: data.access_token,
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
		});

		if (!response.ok) {
			const error = await response.json();
			throw new Error(error.detail || 'Registration failed');
		}

		const data = await response.json();

		// Store tokens
		localStorage.setItem('access_token', data.access_token);
		if (data.refresh_token) {
			localStorage.setItem('refresh_token', data.refresh_token);
		}

		// Clear guest data if any
		localStorage.removeItem('guest_token');
		localStorage.removeItem('guest_created_at');

		return {
			user: data.user,
			tokens: {
				access_token: data.access_token,
				refresh_token: data.refresh_token,
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
		});

		if (!response.ok) {
			const error = await response.json();
			throw new Error(error.detail || 'Login failed');
		}

		const data = await response.json();

		// Store tokens
		localStorage.setItem('access_token', data.access_token);
		if (data.refresh_token) {
			localStorage.setItem('refresh_token', data.refresh_token);
		}

		// Clear guest data
		localStorage.removeItem('guest_token');
		localStorage.removeItem('guest_created_at');

		return {
			user: data.user,
			tokens: {
				access_token: data.access_token,
				refresh_token: data.refresh_token,
			},
		};
	},

	/**
	 * Claim a guest account with email and password
	 */
	async claimGuest(
		email: string,
		password: string
	): Promise<{ user: User; tokens: AuthTokens }> {
		const guestToken = localStorage.getItem('guest_token');

		if (!guestToken) {
			throw new Error('No guest account to claim');
		}

		const response = await fetch(`${API_URL}/api/v1/auth/claim-guest`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ guest_token: guestToken, email, password }),
		});

		if (!response.ok) {
			const error = await response.json();
			throw new Error(error.detail || 'Failed to claim account');
		}

		const data = await response.json();

		// Update tokens
		localStorage.setItem('access_token', data.access_token);
		if (data.refresh_token) {
			localStorage.setItem('refresh_token', data.refresh_token);
		}

		// Clear guest data
		localStorage.removeItem('guest_token');
		localStorage.removeItem('guest_created_at');

		return {
			user: data.user,
			tokens: {
				access_token: data.access_token,
				refresh_token: data.refresh_token,
			},
		};
	},

	/**
	 * Get current user info
	 */
	async getCurrentUser(): Promise<User | null> {
		const token = localStorage.getItem('access_token');

		if (!token) {
			return null;
		}

		try {
			const response = await fetch(`${API_URL}/api/v1/auth/me`, {
				headers: {
					Authorization: `Bearer ${token}`,
				},
			});

			if (!response.ok) {
				// Token is invalid
				this.logout();
				return null;
			}

			return await response.json();
		} catch (error) {
			console.error('Failed to get current user:', error);
			return null;
		}
	},

	/**
	 * Logout (clear all auth data)
	 */
	logout(): void {
		localStorage.removeItem('access_token');
		localStorage.removeItem('refresh_token');
		localStorage.removeItem('guest_token');
		localStorage.removeItem('guest_created_at');
	},

	/**
	 * Check if user is currently a guest
	 */
	isGuest(): boolean {
		return !!localStorage.getItem('guest_token');
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
	 */
	getAuthHeader(): HeadersInit {
		const token = localStorage.getItem('access_token');

		if (!token) {
			return {};
		}

		return {
			Authorization: `Bearer ${token}`,
		};
	},

	/**
	 * Check if user is authenticated
	 */
	isAuthenticated(): boolean {
		return !!localStorage.getItem('access_token');
	},
};
