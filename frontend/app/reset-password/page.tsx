"use client";

import { API_URL } from "@/lib/api-client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

function ResetPasswordForm() {
	const searchParams = useSearchParams();
	const token = searchParams.get("token");
	const [password, setPassword] = useState("");
	const [confirmPassword, setConfirmPassword] = useState("");
	const [submitted, setSubmitted] = useState(false);
	const [error, setError] = useState("");
	const [loading, setLoading] = useState(false);

	if (!token) {
		return (
			<div className="min-h-screen flex items-center justify-center bg-background p-4">
				<div className="w-full max-w-md space-y-6 text-center">
					<div className="text-4xl">⚠️</div>
					<h1 className="text-2xl font-bold text-foreground">Invalid reset link</h1>
					<p className="text-muted-foreground">
						This password reset link is invalid or has expired.
					</p>
					<Link href="/forgot-password" className="text-primary hover:underline block mt-4">
						Request a new reset link
					</Link>
				</div>
			</div>
		);
	}

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		setError("");

		if (password !== confirmPassword) {
			setError("Passwords don't match");
			return;
		}

		setLoading(true);

		try {
			const response = await fetch(`${API_URL}/api/v1/auth/reset-password`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ token, password }),
			});

			if (!response.ok) {
				const data = await response.json();
				// Handle validation errors (password policy)
				if (data.detail && typeof data.detail === "object" && Array.isArray(data.detail)) {
					const messages = data.detail.map((d: { msg?: string }) => d.msg || "").filter(Boolean);
					throw new Error(messages.join(". ") || "Validation failed");
				}
				throw new Error(data.detail || data.message || "Something went wrong");
			}

			setSubmitted(true);
		} catch (err: unknown) {
			setError(err instanceof Error ? err.message : "Something went wrong");
		} finally {
			setLoading(false);
		}
	};

	if (submitted) {
		return (
			<div className="min-h-screen flex items-center justify-center bg-background p-4">
				<div className="w-full max-w-md space-y-6 text-center">
					<div className="text-4xl">✅</div>
					<h1 className="text-2xl font-bold text-foreground">Password reset!</h1>
					<p className="text-muted-foreground">
						Your password has been successfully reset. You can now log in with your new password.
					</p>
					<Link
						href="/auth/login"
						className="inline-block py-2 px-6 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 mt-4"
					>
						Log in
					</Link>
				</div>
			</div>
		);
	}

	return (
		<div className="min-h-screen flex items-center justify-center bg-background p-4">
			<div className="w-full max-w-md space-y-6">
				<div className="text-center">
					<h1 className="text-2xl font-bold text-foreground">Choose a new password</h1>
					<p className="text-muted-foreground mt-2">
						Must be at least 12 characters with uppercase, lowercase, digits, and special characters
					</p>
				</div>

				<form onSubmit={handleSubmit} className="space-y-4">
					<div>
						<label htmlFor="password" className="block text-sm font-medium text-foreground mb-1">
							New Password
						</label>
						<input
							id="password"
							type="password"
							value={password}
							onChange={(e) => setPassword(e.target.value)}
							required
							minLength={12}
							className="w-full px-3 py-2 bg-card border border-border rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
						/>
					</div>

					<div>
						<label htmlFor="confirmPassword" className="block text-sm font-medium text-foreground mb-1">
							Confirm Password
						</label>
						<input
							id="confirmPassword"
							type="password"
							value={confirmPassword}
							onChange={(e) => setConfirmPassword(e.target.value)}
							required
							className="w-full px-3 py-2 bg-card border border-border rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
						/>
					</div>

					{error && (
						<div className="text-red-400 text-sm whitespace-pre-wrap">{error}</div>
					)}

					<button
						type="submit"
						disabled={loading}
						className="w-full py-2 px-4 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 disabled:opacity-50"
					>
						{loading ? "Resetting..." : "Reset password"}
					</button>
				</form>
			</div>
		</div>
	);
}

export default function ResetPasswordPage() {
	return (
		<Suspense fallback={
			<div className="min-h-screen flex items-center justify-center bg-background">
				<p className="text-muted-foreground">Loading...</p>
			</div>
		}>
			<ResetPasswordForm />
		</Suspense>
	);
}
