import { authService, type User } from '@/lib/auth';
import { useTranslation } from '@/lib/hooks/useTranslation';
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
	const { t } = useTranslation();
	const router = useRouter();
	const [isLoading, setIsLoading] = useState(true);
	const [user, setUser] = useState<User | null>(null);

	useEffect(() => {
		checkAuth();
	}, []);

	const checkAuth = async () => {
		try {
			// Validate auth by fetching current user (backend checks httpOnly cookie)
			const currentUser = await authService.getCurrentUser();

			if (!currentUser) {
				// No valid session, redirect to login
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
					<p className="mt-4 text-gray-600">{t('common.loading')}</p>
				</div>
			</div>
		);
	}

	// Render children if authenticated
	return <>{children}</>;
}
