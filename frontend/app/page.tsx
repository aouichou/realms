"use client";

import { useAuth } from "@/lib/contexts/AuthContext";
import { useTranslation } from "@/lib/hooks/useTranslation";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function Home() {
	const { t } = useTranslation();
	const router = useRouter();
	const { user, isLoading } = useAuth();

	// Redirect authenticated users to character selection
	useEffect(() => {
		if (!isLoading && user) {
			router.push('/character/select');
		}
	}, [user, isLoading, router]);

	// Show loading state while checking auth
	if (isLoading) {
		return (
			<div className="flex min-h-screen items-center justify-center bg-linear-to-br from-primary-900 via-secondary-600 to-primary-900">
				<div className="text-center">
					<div className="text-4xl mb-4 animate-bounce">⚔️</div>
					<p className="text-lg font-body text-accent-200">Loading...</p>
				</div>
			</div>
		);
	}

	// Don't render home page if user is authenticated (will redirect)
	if (user) {
		return null;
	}

	return (
		<div className="flex min-h-screen flex-col items-center justify-center bg-linear-to-br from-primary-900 via-secondary-600 to-primary-900 px-4">
			<main className="flex flex-col items-center gap-6 md:gap-8 text-center max-w-4xl w-full">
				{/* Logo/Title with fade-in animation */}
				<div className="flex flex-col items-center gap-3 md:gap-4 animate-fadeIn">
					<h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-display text-accent-200 hover:text-accent-400 transition-colors duration-300">
						{t("home.title")}
					</h1>
					<p className="text-xl font-body text-accent-200/80">
						{t("home.subtitle")}
					</p>
				</div>

				{/* Description */}
				<div className="max-w-2xl space-y-4 font-body text-narrative animate-fadeIn animation-delay-200">
					<p className="text-accent-200">
						{t("home.description1")}
					</p>
					<p className="text-accent-200/70">
						{t("home.description2")}
					</p>
				</div>

				{/* CTA Buttons with stagger animation */}
				<div className="mt-6 md:mt-8 flex flex-col gap-3 md:gap-4 w-full sm:w-auto items-center animate-fadeIn animation-delay-400">
					<div className="flex flex-col sm:flex-row gap-3 md:gap-4 w-full sm:w-auto justify-center">
						<Link
							href="/auth/login"
							className="group inline-flex items-center justify-center gap-2 rounded-lg bg-accent-600 px-6 md:px-8 py-3 md:py-4 text-base md:text-lg font-body font-semibold text-primary-900 transition-all hover:bg-accent-400 hover:scale-105 hover:shadow-2xl shadow-lg active:scale-95"
						>
							{t("home.signIn")}
							<svg
								className="h-5 w-5 transition-transform group-hover:translate-x-1"
								fill="none"
								stroke="currentColor"
								viewBox="0 0 24 24"
							>
								<path
									strokeLinecap="round"
									strokeLinejoin="round"
									strokeWidth={2}
									d="M13 7l5 5m0 0l-5 5m5-5H6"
								/>
							</svg>
						</Link>

						<Link
							href="/auth/register"
							className="inline-flex items-center justify-center gap-2 rounded-lg bg-secondary-600 px-6 md:px-8 py-3 md:py-4 text-base md:text-lg font-body font-semibold text-white transition-all hover:bg-accent-400 hover:text-primary-900 hover:scale-105 hover:shadow-2xl shadow-lg active:scale-95"
						>
							{t("home.register")}
						</Link>
					</div>

					<p className="text-sm text-accent-200/70 font-body">
						{t("home.or")}
					</p>

					<Link
						href="/demo"
						className="inline-flex items-center justify-center gap-2 rounded-lg border-2 border-accent-600 px-6 md:px-8 py-2 md:py-3 text-sm md:text-base font-body font-semibold text-accent-200 transition-all hover:bg-accent-600 hover:text-primary-900 hover:scale-105 hover:shadow-2xl shadow-lg active:scale-95"
					>
						🎮 {t("home.tryDemo")}
					</Link>

					<p className="text-xs text-accent-200/60 font-body max-w-md text-center mt-2">
						{t("home.noEmailRequired")}
					</p>
				</div>

				{/* Features with stagger animation */}
				<div className="mt-8 md:mt-12 grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6 w-full animate-fadeIn animation-delay-600">
					<div className="p-4 md:p-6 bg-accent-200/10 backdrop-blur-sm rounded-lg border border-accent-600/40 transition-all hover:scale-105 hover:shadow-lg hover:border-accent-600">
						<div className="text-3xl mb-3">⚔️</div>
						<h3 className="font-display text-xl text-accent-200 mb-2">{t("home.features.classes.title")}</h3>
						<p className="text-sm font-body text-accent-200/70">
							{t("home.features.classes.description")}
						</p>
					</div>

					<div className="p-6 bg-accent-200/10 backdrop-blur-sm rounded-lg border border-accent-600/40 transition-all hover:scale-105 hover:shadow-lg hover:border-accent-600 animation-delay-100">
						<div className="text-3xl mb-3">🎲</div>
						<h3 className="font-display text-xl text-accent-200 mb-2">{t("home.features.randomness.title")}</h3>
						<p className="text-sm font-body text-accent-200/70">
							{t("home.features.randomness.description")}
						</p>
					</div>

					<div className="p-6 bg-accent-200/10 backdrop-blur-sm rounded-lg border border-accent-600/40 transition-all hover:scale-105 hover:shadow-lg hover:border-accent-600 animation-delay-200">
						<div className="text-3xl mb-3">🤖</div>
						<h3 className="font-display text-xl text-accent-200 mb-2">{t("home.features.aiDM.title")}</h3>
						<p className="text-sm font-body text-accent-200/70">
							{t("home.features.aiDM.description")}
						</p>
					</div>
				</div>

				{/* Tech Stack Pills with fade-in */}
				<div className="mt-8 flex flex-wrap justify-center gap-3 animate-fadeIn animation-delay-800">
					<span className="rounded-full bg-accent-200/10 backdrop-blur-sm border border-accent-600/40 px-4 py-2 text-sm font-body text-accent-200 transition-all hover:scale-110 hover:border-accent-600 cursor-default">
						Next.js 16
					</span>
					<span className="rounded-full bg-accent-200/10 backdrop-blur-sm border border-accent-600/40 px-4 py-2 text-sm font-body text-accent-200 transition-all hover:scale-110 hover:border-accent-600 cursor-default">
						FastAPI + PostgreSQL
					</span>
					<span className="rounded-full bg-accent-200/10 backdrop-blur-sm border border-accent-600/40 px-4 py-2 text-sm font-body text-accent-200 transition-all hover:scale-110 hover:border-accent-600 cursor-default">
						Redis Sessions
					</span>
					<span className="rounded-full bg-accent-400/20 border border-accent-600 px-4 py-2 text-sm font-body text-accent-600 transition-all hover:scale-110 hover:bg-accent-400/30 cursor-default">
						Mistral AI
					</span>
				</div>
			</main>

			{/* Footer */}
			<footer className="mt-16 text-sm font-body text-accent-200/60">
				<p>{t("home.footer")}</p>
			</footer>
		</div>
	);
}
