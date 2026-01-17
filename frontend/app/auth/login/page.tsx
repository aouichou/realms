'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useToast } from '@/components/ui/toast';
import { authService } from '@/lib/auth';
import { useTranslation } from '@/lib/hooks/useTranslation';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

export default function LoginPage() {
	const router = useRouter();
	const { showToast } = useToast();
	const { t } = useTranslation();
	const [email, setEmail] = useState('');
	const [password, setPassword] = useState('');
	const [isLoading, setIsLoading] = useState(false);

	const handleLogin = async (e: React.FormEvent) => {
		e.preventDefault();
		setIsLoading(true);

		try {
			await authService.login(email, password);
			showToast(t('auth.login.welcomeBack'), 'success');
			router.push('/character/select');
		} catch (error: any) {
			showToast(error.message || t('auth.login.loginFailed'), 'error');
		} finally {
			setIsLoading(false);
		}
	};

	const handleGuestMode = async () => {
		setIsLoading(true);

		try {
			await authService.createGuest();
			showToast(t('auth.login.welcomeAdventurer'), 'success');
			router.push('/character/create');
		} catch (error: any) {
			showToast(error.message || t('auth.login.guestFailed'), 'error');
		} finally {
			setIsLoading(false);
		}
	};

	return (
		<div className="min-h-screen flex items-center justify-center bg-linear-to-br from-neutral-900 via-neutral-800 to-neutral-900 p-4">
			<Card className="w-full max-w-md">
				<CardHeader className="space-y-2 text-center">
					<CardTitle className="font-display text-3xl">{t('auth.login.title')}</CardTitle>
					<CardDescription className="font-body">
						{t('auth.login.subtitle')}
					</CardDescription>
				</CardHeader>
				<CardContent className="space-y-4">
					<form onSubmit={handleLogin} className="space-y-4">
						<div className="space-y-2">
							<Label htmlFor="email">{t('auth.login.email')}</Label>
							<Input
								id="email"
								type="email"
								placeholder={t('auth.login.emailPlaceholder')}
								value={email}
								onChange={(e) => setEmail(e.target.value)}
								required
							/>
						</div>

						<div className="space-y-2">
							<Label htmlFor="password">{t('auth.login.password')}</Label>
							<Input
								id="password"
								type="password"
								placeholder={t('auth.login.passwordPlaceholder')}
								value={password}
								onChange={(e) => setPassword(e.target.value)}
								required
								minLength={8}
							/>
						</div>

						<Button
							type="submit"
							className="w-full font-body"
							disabled={isLoading}
						>
							{isLoading ? t('auth.login.signingIn') : t('auth.login.signIn')}
						</Button>
					</form>

					<div className="relative">
						<div className="absolute inset-0 flex items-center">
							<span className="w-full border-t" />
						</div>
						<div className="relative flex justify-center text-xs uppercase">
							<span className="bg-background px-2 text-muted-foreground">
								{t('auth.login.orContinueAs')}
							</span>
						</div>
					</div>

					<Button
						variant="outline"
						className="w-full font-body"
						onClick={handleGuestMode}
						disabled={isLoading}
					>
						{t('auth.login.guestMode')}
					</Button>

					<p className="text-center text-sm text-muted-foreground font-body">
						{t('auth.login.noAccount')}{' '}
						<Link
							href="/auth/register"
							className="text-primary hover:underline font-medium"
						>
							{t('auth.login.registerHere')}
						</Link>
					</p>
				</CardContent>
			</Card>
		</div>
	);
}
