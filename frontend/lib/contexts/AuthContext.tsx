"use client";

import { authService, type User } from "@/lib/auth";
import { willExpireSoon } from "@/lib/jwt";
import { useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useRef, useState } from "react";

interface AuthContextType {
	user: User | null;
	isLoading: boolean;
	isAuthenticated: boolean;
	isGuest: boolean;
	login: (email: string, password: string) => Promise<void>;
	register: (email: string, username: string, password: string) => Promise<void>;
	logout: () => Promise<void>;
	createGuest: () => Promise<void>;
	refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
	const [user, setUser] = useState<User | null>(null);
	const [isLoading, setIsLoading] = useState(true);
	const [accessToken, setAccessToken] = useState<string | null>(null); // Store token for expiry checking
	const refreshTimerRef = useRef<NodeJS.Timeout | null>(null);
	const router = useRouter();

	// Check auth status on mount and try to restore session
	useEffect(() => {
		initializeAuth();

		// Cleanup refresh timer on unmount
		return () => {
			if (refreshTimerRef.current) {
				clearInterval(refreshTimerRef.current);
			}
		};
	}, []);

	// Proactive token refresh - check every minute
	useEffect(() => {
		if (!accessToken || !user) {
			return;
		}

		// Clear existing timer
		if (refreshTimerRef.current) {
			clearInterval(refreshTimerRef.current);
		}

		// Set up periodic check (every 60 seconds)
		refreshTimerRef.current = setInterval(async () => {
			// Check if token will expire in the next 5 minutes
			if (willExpireSoon(accessToken, 5 * 60 * 1000)) {
				try {
					const refreshed = await authService.refreshToken();
					if (refreshed && refreshed.access_token) {
						setAccessToken(refreshed.access_token);
					} else {
						// Refresh failed, logout
						await logout();
					}
				} catch (error) {
					console.error('[AuthContext] Proactive token refresh failed:', error);
					await logout();
				}
			}
		}, 60 * 1000); // Check every minute

		return () => {
			if (refreshTimerRef.current) {
				clearInterval(refreshTimerRef.current);
			}
		};
	}, [accessToken, user]);

	const initializeAuth = async () => {
		try {
			// With httpOnly cookies, we can't check tokens from client
			// Instead, try to get current user - backend validates cookie
			const currentUser = await authService.getCurrentUser();

			if (currentUser) {
				// Valid session, user is logged in
				setUser(currentUser);
			} else {
				// No valid session - try to refresh
				const refreshed = await authService.refreshToken();

				if (refreshed) {
					// Refresh successful, get user again
					const refreshedUser = await authService.getCurrentUser();
					setUser(refreshedUser);
				} else {
					// Refresh failed - user needs to log in
					await authService.logout();
				}
			}
		} catch (error) {
			console.error('[AuthContext] Failed to initialize auth:', error);
			await authService.logout();
		} finally {
			setIsLoading(false);
		}
	};

	const login = async (email: string, password: string) => {
		const { user, tokens } = await authService.login(email, password);
		setUser(user);
		setAccessToken(tokens.access_token); // Store for expiry checking
	};

	const register = async (email: string, username: string, password: string) => {
		const { user, tokens } = await authService.register(email, username, password);
		setUser(user);
		setAccessToken(tokens.access_token); // Store for expiry checking
	};

	const createGuest = async () => {
		const { user, tokens } = await authService.createGuest();
		setUser(user);
		setAccessToken(tokens.access_token); // Store for expiry checking
	};

	const logout = async () => {
		await authService.logout();
		setUser(null);
		setAccessToken(null);

		// Clear refresh timer
		if (refreshTimerRef.current) {
			clearInterval(refreshTimerRef.current);
		}

		router.push('/');
	};

	const refreshUser = async () => {
		const currentUser = await authService.getCurrentUser();
		setUser(currentUser);
	};

	const value: AuthContextType = {
		user,
		isLoading,
		isAuthenticated: !!user && !user.is_guest,
		isGuest: !!user && user.is_guest,
		login,
		register,
		logout,
		createGuest,
		refreshUser,
	};

	return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/**
 * Hook to use auth context
 * @throws Error if used outside AuthProvider
 */
export function useAuth() {
	const context = useContext(AuthContext);
	if (context === undefined) {
		throw new Error('useAuth must be used within an AuthProvider');
	}
	return context;
}

/**
 * HOC to protect routes that require authentication
 * Redirects to login if not authenticated
 */
export function withAuth<P extends object>(
	Component: React.ComponentType<P>,
	options: { redirectTo?: string; allowGuest?: boolean } = {}
) {
	return function ProtectedRoute(props: P) {
		const { isAuthenticated, isGuest, isLoading } = useAuth();
		const router = useRouter();

		useEffect(() => {
			if (!isLoading) {
				const isAuthorized = options.allowGuest
					? (isAuthenticated || isGuest)
					: isAuthenticated;

				if (!isAuthorized) {
					router.push(options.redirectTo || '/');
				}
			}
		}, [isAuthenticated, isGuest, isLoading, router]);

		if (isLoading) {
			return (
				<div className="flex items-center justify-center min-h-screen">
					<div className="text-white">Loading...</div>
				</div>
			);
		}

		const isAuthorized = options.allowGuest
			? (isAuthenticated || isGuest)
			: isAuthenticated;

		if (!isAuthorized) {
			return null;
		}

		return <Component {...props} />;
	};
}
