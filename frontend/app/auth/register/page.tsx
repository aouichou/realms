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

export default function RegisterPage() {
	const router = useRouter();
	const { showToast } = useToast();
	const { t } = useTranslation();
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
			await authService.register(formData.email, formData.username, formData.password);
			showToast(t('auth.register.accountCreated'), 'success');
			router.push('/character/create');
		} catch (error: any) {
			showToast(error.message || t('auth.register.registerFailed'), 'error');
		} finally {
			setIsLoading(false);
		}
	};

	return (
		<div className="min-h-screen flex items-center justify-center bg-linear-to-br from-neutral-900 via-neutral-800 to-neutral-900 p-4">
			<Card className="w-full max-w-md">
				<CardHeader className="space-y-2 text-center">
					<CardTitle className="font-display text-3xl">{t('auth.register.title')}</CardTitle>
					<CardDescription className="font-body">
						{t('auth.register.subtitle')}
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
							className="w-full font-body"
							disabled={isLoading}
						>
							{isLoading ? 'Creating Account...' : 'Create Account'}
						</Button>
					</form>

					<p className="text-center text-sm text-muted-foreground font-body">
						{t('auth.register.haveAccount')}{' '}
						<Link
							href="/auth/login"
							className="text-primary hover:underline font-medium"
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
