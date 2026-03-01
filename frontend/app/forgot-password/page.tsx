"use client";

import { API_URL } from "@/lib/api-client";
import Link from "next/link";
import { useState } from "react";

export default function ForgotPasswordPage() {
	const [email, setEmail] = useState("");
	const [submitted, setSubmitted] = useState(false);
	const [error, setError] = useState("");
	const [loading, setLoading] = useState(false);

	const handleSubmit = async (e: React.FormEvent) => {
		e.preventDefault();
		setError("");
		setLoading(true);

		try {
			const response = await fetch(`${API_URL}/api/v1/auth/forgot-password`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ email }),
			});

			if (!response.ok) {
				const data = await response.json();
				throw new Error(data.detail || "Something went wrong");
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
					<div className="text-4xl">📧</div>
					<h1 className="text-2xl font-bold text-foreground">Check your email</h1>
					<p className="text-muted-foreground">
						If an account with <strong>{email}</strong> exists, we&apos;ve sent a password reset link.
						It expires in 30 minutes.
					</p>
					<Link href="/auth/login" className="text-primary hover:underline block mt-4">
						Back to login
					</Link>
				</div>
			</div>
		);
	}

	return (
		<div className="min-h-screen flex items-center justify-center bg-background p-4">
			<div className="w-full max-w-md space-y-6">
				<div className="text-center">
					<h1 className="text-2xl font-bold text-foreground">Reset your password</h1>
					<p className="text-muted-foreground mt-2">
						Enter your email and we&apos;ll send you a reset link
					</p>
				</div>

				<form onSubmit={handleSubmit} className="space-y-4">
					<div>
						<label htmlFor="email" className="block text-sm font-medium text-foreground mb-1">
							Email
						</label>
						<input
							id="email"
							type="email"
							value={email}
							onChange={(e) => setEmail(e.target.value)}
							required
							className="w-full px-3 py-2 bg-card border border-border rounded-lg text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
							placeholder="your@email.com"
						/>
					</div>

					{error && (
						<div className="text-red-400 text-sm">{error}</div>
					)}

					<button
						type="submit"
						disabled={loading}
						className="w-full py-2 px-4 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 disabled:opacity-50"
					>
						{loading ? "Sending..." : "Send reset link"}
					</button>
				</form>

				<div className="text-center text-sm text-muted-foreground">
					Remember your password?{" "}
					<Link href="/auth/login" className="text-primary hover:underline">
						Log in
					</Link>
				</div>
			</div>
		</div>
	);
}
