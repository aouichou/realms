"use client";

import { API_URL } from "@/lib/api-client";
import { authService, type User } from "@/lib/auth";
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
	claimGuest: (email: string, username: string, password: string) => Promise<void>;
	refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
	const [user, setUser] = useState<User | null>(null);
	const [isLoading, setIsLoading] = useState(true);
	const refreshTimerRef = useRef<NodeJS.Timeout | null>(null);
	const router = useRouter();

	useEffect(() => {
		initializeAuth();
		return () => {
			if (refreshTimerRef.current) {
				clearInterval(refreshTimerRef.current);
			}
		};
	}, []);

	// Proactive token refresh via /token-status endpoint
	useEffect(() => {
		if (!user) {
			if (refreshTimerRef.current) {
				clearInterval(refreshTimerRef.current);
			}
			return;
		}

		refreshTimerRef.current = setInterval(async () => {
			try {
				const response = await fetch(`${API_URL}/api/v1/auth/token-status`, {
					credentials: 'include',
				});

				if (!response.ok) {
					await logout();
					return;
				}

				const status = await response.json();
				if (status.should_refresh) {
					const success = await authService.refreshToken();
					if (!success) {
						await logout();
					}
				}
			} catch (error) {
				console.error('[AuthContext] Token status check failed:', error);
			}
		}, 60 * 1000);

		return () => {
			if (refreshTimerRef.current) {
				clearInterval(refreshTimerRef.current);
			}
		};
	}, [user]);

	const initializeAuth = async () => {
		try {
			const currentUser = await authService.getCurrentUser();
			if (currentUser) {
				setUser(currentUser);
			} else {
				const success = await authService.refreshToken();
				if (success) {
					const refreshedUser = await authService.getCurrentUser();
					setUser(refreshedUser);
				} else {
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

	const claimGuest = async (email: string, username: string, password: string) => {
		const { user } = await authService.claimGuest(email, username, password);
		setUser(user);
	};

	const logout = async () => {
		await authService.logout();
		setUser(null);
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
		claimGuest,
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
