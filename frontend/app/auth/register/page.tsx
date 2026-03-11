'use client';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useToast } from '@/components/ui/toast';
import { useAuth } from '@/lib/contexts/AuthContext';
import { useTranslation } from '@/lib/hooks/useTranslation';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense, useState } from 'react';

function RegisterForm() {
	const router = useRouter();
	const searchParams = useSearchParams();
	const redirectTo = searchParams.get('redirect');
	const { showToast } = useToast();
	const { t } = useTranslation();
	const { register, claimGuest, isGuest } = useAuth();
	const [formData, setFormData] = useState({
		email: '',
		username: '',
		password: '',
		confirmPassword: '',
	});
	const [isLoading, setIsLoading] = useState(false);

	const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
		setFormData((prev) => ({
			...prev,
			[e.target.name]: e.target.value,
		}));
	};

	const handleRegister = async (e: React.FormEvent) => {
		e.preventDefault();

		if (formData.password !== formData.confirmPassword) {
			showToast(t('auth.register.passwordMismatch'), 'error');
			return;
		}

		setIsLoading(true);

		try {
			if (isGuest) {
				// Claim the guest account — preserves characters and game progress
				await claimGuest(formData.email, formData.username, formData.password);
				showToast(t('auth.register.accountClaimed'), 'success');
			} else {
				await register(formData.email, formData.username, formData.password);
				showToast(t('auth.register.accountCreated'), 'success');
			}
			// Validate redirect target — only allow relative paths to prevent open redirect
			const safeRedirect = redirectTo && redirectTo.startsWith('/') && !redirectTo.startsWith('//') ? redirectTo : '/character/select';
			router.push(safeRedirect);
		} catch (error: any) {
			showToast(error.message || t('auth.register.registerFailed'), 'error');
		} finally {
			setIsLoading(false);
		}
	};

	return (
		<div className="min-h-screen flex items-center justify-center bg-linear-to-br from-primary-900 via-secondary-600 to-primary-900 p-4">
			<Card className="w-full max-w-md border-neutral-500/20 shadow-2xl">
				<CardHeader className="space-y-2 text-center">
					<CardTitle className="font-display text-3xl">
						{isGuest ? t('auth.register.claimTitle') : t('auth.register.title')}
					</CardTitle>
					<CardDescription className="font-body">
						{isGuest
							? t('auth.register.claimSubtitle')
							: t('auth.register.subtitle')}
					</CardDescription>
				</CardHeader>
				<CardContent className="space-y-4">
					<form onSubmit={handleRegister} className="space-y-4">
						<div className="space-y-2">
							<Label htmlFor="email">{t('auth.register.email')}</Label>
							<Input
								id="email"
								name="email"
								type="email"
								placeholder={t('auth.register.emailPlaceholder')}
								value={formData.email}
								onChange={handleChange}
								required
							/>
						</div>

						<div className="space-y-2">
							<Label htmlFor="username">{t('auth.register.username')}</Label>
							<Input
								id="username"
								name="username"
								type="text"
								placeholder={t('auth.register.usernamePlaceholder')}
								value={formData.username}
								onChange={handleChange}
								required
								minLength={3}
								maxLength={100}
							/>
						</div>

						<div className="space-y-2">
							<Label htmlFor="password">{t('auth.register.password')}</Label>
							<Input
								id="password"
								name="password"
								type="password"
								placeholder={t('auth.register.passwordPlaceholder')}
								value={formData.password}
								onChange={handleChange}
								required
								minLength={8}
							/>
						</div>

						<div className="space-y-2">
							<Label htmlFor="confirmPassword">{t('auth.register.confirmPassword')}</Label>
							<Input
								id="confirmPassword"
								name="confirmPassword"
								type="password"
								placeholder={t('auth.register.passwordPlaceholder')}
								value={formData.confirmPassword}
								onChange={handleChange}
								required
								minLength={8}
							/>
						</div>

						<Button
							type="submit"
							className="w-full font-body bg-accent-600 hover:bg-accent-400 text-primary-900 font-semibold"
							disabled={isLoading}
						>
							{isLoading
								? t('auth.register.creatingAccount')
								: isGuest
									? t('auth.register.claimButton')
									: t('auth.register.createButton')}
						</Button>
					</form>

					<p className="text-center text-sm text-accent-200/70 font-body">
						{t('auth.register.haveAccount')}{' '}
						<Link
							href="/auth/login"
							className="text-accent-400 hover:text-accent-200 hover:underline font-semibold"
						>
							{t('auth.register.signInHere')}
						</Link>
					</p>

					<p className="text-center text-xs text-muted-foreground font-body">
						{t('auth.register.agreementText')}
					</p>
				</CardContent>
			</Card>
		</div>
	);
}

export default function RegisterPage() {
	return (
		<Suspense fallback={
			<div className="min-h-screen flex items-center justify-center bg-linear-to-br from-primary-900 via-secondary-600 to-primary-900">
				<p className="text-accent-200/70">Loading...</p>
			</div>
		}>
			<RegisterForm />
		</Suspense>
	);
}
