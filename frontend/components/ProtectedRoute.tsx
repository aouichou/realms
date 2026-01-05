import { authService, type User } from '@/lib/auth';
import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';

interface ProtectedRouteProps {
	children: React.ReactNode;
	requireRegistered?: boolean; // If true, guests will be redirected
}

/**
 * ProtectedRoute component to guard authenticated routes
 * Redirects to login if not authenticated
 * Optionally redirects guests to claim account flow
 */
export function ProtectedRoute({ children, requireRegistered = false }: ProtectedRouteProps) {
	const router = useRouter();
	const [isLoading, setIsLoading] = useState(true);
	const [user, setUser] = useState<User | null>(null);

	useEffect(() => {
		checkAuth();
	}, []);

	const checkAuth = async () => {
		try {
			// Check for access token
			const token = localStorage.getItem('access_token');

			if (!token) {
				// No token, redirect to login
				router.push('/login?redirect=' + encodeURIComponent(router.asPath));
				return;
			}

			// Validate token by fetching current user
			const currentUser = await authService.getCurrentUser();

			if (!currentUser) {
				// Invalid token, redirect to login
				localStorage.removeItem('access_token');
				localStorage.removeItem('refresh_token');
				router.push('/login?redirect=' + encodeURIComponent(router.asPath));
				return;
			}

			// Check if route requires registered user
			if (requireRegistered && currentUser.is_guest) {
				router.push('/claim-account?redirect=' + encodeURIComponent(router.asPath));
				return;
			}

			setUser(currentUser);
			setIsLoading(false);
		} catch (error) {
			console.error('Auth check failed:', error);
			// On error, redirect to login
			router.push('/login?redirect=' + encodeURIComponent(router.asPath));
		}
	};

	// Show loading state while checking auth
	if (isLoading) {
		return (
			<div className="flex items-center justify-center min-h-screen">
				<div className="text-center">
					<div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
					<p className="mt-4 text-gray-600">Loading...</p>
				</div>
			</div>
		);
	}

	// Render children if authenticated
	return <>{children}</>;
}
