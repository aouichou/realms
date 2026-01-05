'use client';

import { Button } from '@/components/ui/button';
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useToast } from '@/components/ui/toast';
import { authService } from '@/lib/auth';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

export function ClaimAccountModal() {
	const router = useRouter();
	const { showToast } = useToast();
	const [isOpen, setIsOpen] = useState(false);
	const [formData, setFormData] = useState({
		email: '',
		password: '',
		confirmPassword: '',
	});
	const [isLoading, setIsLoading] = useState(false);

	useEffect(() => {
		// Check every minute if we should prompt
		const interval = setInterval(() => {
			if (authService.shouldPromptClaim()) {
				setIsOpen(true);
			}
		}, 60000); // Check every minute

		// Check immediately on mount
		if (authService.shouldPromptClaim()) {
			setIsOpen(true);
		}

		return () => clearInterval(interval);
	}, []);

	const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
		setFormData((prev) => ({
			...prev,
			[e.target.name]: e.target.value,
		}));
	};

	const handleClaim = async (e: React.FormEvent) => {
		e.preventDefault();

		if (formData.password !== formData.confirmPassword) {
			showToast('Passwords do not match', 'error');
			return;
		}

		setIsLoading(true);

		try {
			await authService.claimGuest(formData.email, formData.password);
			showToast('Account claimed successfully! Your progress is saved.', 'success');
			setIsOpen(false);
			router.refresh();
		} catch (error: any) {
			showToast(error.message || 'Failed to claim account', 'error');
		} finally {
			setIsLoading(false);
		}
	};

	const handleDismiss = () => {
		setIsOpen(false);
		// Set a flag to not show again for this session
		sessionStorage.setItem('claim_prompt_dismissed', 'true');
	};

	// Don't show if user dismissed in this session
	if (typeof window !== 'undefined' && sessionStorage.getItem('claim_prompt_dismissed')) {
		return null;
	}

	return (
		<Dialog open={isOpen} onOpenChange={setIsOpen}>
			<DialogContent className="sm:max-w-md">
				<DialogHeader>
					<DialogTitle className="font-display text-2xl">Save Your Progress</DialogTitle>
					<DialogDescription className="font-body">
						You've been playing for 30 minutes! Create an account to save your character and
						adventure progress.
					</DialogDescription>
				</DialogHeader>

				<form onSubmit={handleClaim} className="space-y-4">
					<div className="space-y-2">
						<Label htmlFor="email">Email</Label>
						<Input
							id="email"
							name="email"
							type="email"
							placeholder="your@email.com"
							value={formData.email}
							onChange={handleChange}
							required
						/>
					</div>

					<div className="space-y-2">
						<Label htmlFor="password">Password</Label>
						<Input
							id="password"
							name="password"
							type="password"
							placeholder="••••••••"
							value={formData.password}
							onChange={handleChange}
							required
							minLength={8}
						/>
					</div>

					<div className="space-y-2">
						<Label htmlFor="confirmPassword">Confirm Password</Label>
						<Input
							id="confirmPassword"
							name="confirmPassword"
							type="password"
							placeholder="••••••••"
							value={formData.confirmPassword}
							onChange={handleChange}
							required
							minLength={8}
						/>
					</div>

					<DialogFooter className="gap-2 sm:gap-0">
						<Button
							type="button"
							variant="ghost"
							onClick={handleDismiss}
							disabled={isLoading}
						>
							Maybe Later
						</Button>
						<Button type="submit" disabled={isLoading}>
							{isLoading ? 'Claiming...' : 'Claim Account'}
						</Button>
					</DialogFooter>
				</form>
			</DialogContent>
		</Dialog>
	);
}
