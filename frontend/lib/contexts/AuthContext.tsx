"use client";

import { authService, type User } from "@/lib/auth";
import { useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useState } from "react";

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
	const router = useRouter();

	// Check auth status on mount and try to restore session
	useEffect(() => {
		initializeAuth();
	}, []);

	const initializeAuth = async () => {
		console.log('[AuthContext] Initializing auth...');
		try {
			// With httpOnly cookies, we can't check tokens from client
			// Instead, try to get current user - backend validates cookie
			console.log('[AuthContext] Checking auth with backend...');

			const currentUser = await authService.getCurrentUser();

			if (currentUser) {
				// Valid session, user is logged in
				console.log('[AuthContext] User authenticated:', currentUser.username);
				setUser(currentUser);
			} else {
				// No valid session - try to refresh
				console.log('[AuthContext] No valid session, attempting refresh...');
				const refreshed = await authService.refreshToken();

				if (refreshed) {
					// Refresh successful, get user again
					console.log('[AuthContext] Token refreshed successfully');
					const refreshedUser = await authService.getCurrentUser();
					setUser(refreshedUser);
				} else {
					// Refresh failed - user needs to log in
					console.log('[AuthContext] Token refresh failed, user not authenticated');
					await authService.logout();
				}
			}
		} catch (error) {
			console.error('[AuthContext] Failed to initialize auth:', error);
			await authService.logout();
		} finally {
			setIsLoading(false);
			console.log('[AuthContext] Auth initialization complete');
		}
	};

	const login = async (email: string, password: string) => {
		const { user } = await authService.login(email, password);
		setUser(user);
	};

	const register = async (email: string, username: string, password: string) => {
		const { user } = await authService.register(email, username, password);
		setUser(user);
	};

	const createGuest = async () => {
		const { user } = await authService.createGuest();
		setUser(user);
	};

	const logout = async () => {
		await authService.logout();
		setUser(null);
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
