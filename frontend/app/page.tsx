import Link from "next/link";

export default function Home() {
	return (
		<div className="flex min-h-screen flex-col items-center justify-center bg-background px-4">
			<main className="flex flex-col items-center gap-6 md:gap-8 text-center max-w-4xl w-full">
				{/* Logo/Title with fade-in animation */}
				<div className="flex flex-col items-center gap-3 md:gap-4 animate-fadeIn">
					<h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-display text-primary-900 hover:text-accent-600 transition-colors duration-300">
						Mistral Realms
					</h1>
					<p className="text-xl font-body text-neutral-500">
						AI-Powered D&D Adventures
					</p>
				</div>

				{/* Description */}
				<div className="max-w-2xl space-y-4 font-body text-narrative animate-fadeIn animation-delay-200">
					<p className="text-primary-900">
						Embark on epic adventures guided by an AI Dungeon Master powered by{" "}
						<span className="font-semibold text-accent-600">Mistral AI</span>.
					</p>
					<p className="text-neutral-500">
						Create your character, make choices, and watch your story unfold in real-time with true randomness for dice rolls.
					</p>
				</div>

				{/* CTA Buttons with stagger animation */}
				<div className="mt-6 md:mt-8 flex flex-col gap-3 md:gap-4 w-full sm:w-auto items-center animate-fadeIn animation-delay-400">
					<div className="flex flex-col sm:flex-row gap-3 md:gap-4 w-full sm:w-auto justify-center">
						<Link
							href="/auth/login"
							className="group inline-flex items-center justify-center gap-2 rounded-lg bg-primary-900 px-6 md:px-8 py-3 md:py-4 text-base md:text-lg font-body font-semibold text-white transition-all hover:bg-accent-600 hover:scale-105 hover:shadow-2xl shadow-lg active:scale-95"
						>
							Sign In
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
							Register
						</Link>
					</div>

					<p className="text-sm text-neutral-500 font-body">
						or
					</p>

					<Link
						href="/auth/login"
						className="inline-flex items-center justify-center gap-2 rounded-lg border-2 border-accent-600 px-6 md:px-8 py-2 md:py-3 text-sm md:text-base font-body font-semibold text-accent-600 transition-all hover:bg-accent-600 hover:text-white hover:scale-105 hover:shadow-2xl shadow-lg active:scale-95"
					>
						Login
					</Link>

					<p className="text-xs text-neutral-400 font-body max-w-md text-center mt-2">
						No email required for demo • All progress auto-saved • Claim account anytime
					</p>
				</div>

				{/* Features with stagger animation */}
				<div className="mt-8 md:mt-12 grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6 w-full animate-fadeIn animation-delay-600">
					<div className="p-4 md:p-6 bg-neutral-100 rounded-lg border border-neutral-500/20 transition-all hover:scale-105 hover:shadow-lg hover:border-accent-600/40">
						<div className="text-3xl mb-3">⚔️</div>
						<h3 className="font-display text-xl text-primary-900 mb-2">12 D&D Classes</h3>
						<p className="text-sm font-body text-neutral-500">
							Choose from Barbarian, Bard, Cleric, Druid, Fighter, Monk, Paladin, Ranger, Rogue, Sorcerer, Warlock, or Wizard
						</p>
					</div>

					<div className="p-6 bg-neutral-100 rounded-lg border border-neutral-500/20 transition-all hover:scale-105 hover:shadow-lg hover:border-accent-600/40 animation-delay-100">
						<div className="text-3xl mb-3">🎲</div>
						<h3 className="font-display text-xl text-primary-900 mb-2">True Randomness</h3>
						<p className="text-sm font-body text-neutral-500">
							Dice rolls powered by Random.org's atmospheric noise for genuine unpredictability
						</p>
					</div>

					<div className="p-6 bg-neutral-100 rounded-lg border border-neutral-500/20 transition-all hover:scale-105 hover:shadow-lg hover:border-accent-600/40 animation-delay-200">
						<div className="text-3xl mb-3">🤖</div>
						<h3 className="font-display text-xl text-primary-900 mb-2">AI Dungeon Master</h3>
						<p className="text-sm font-body text-neutral-500">
							Mistral AI creates dynamic narratives, generates scene images, and responds to your choices
						</p>
					</div>
				</div>

				{/* Tech Stack Pills with fade-in */}
				<div className="mt-8 flex flex-wrap justify-center gap-3 animate-fadeIn animation-delay-800">
					<span className="rounded-full bg-neutral-100 border border-neutral-500/20 px-4 py-2 text-sm font-body text-neutral-900 transition-all hover:scale-110 hover:border-accent-600 cursor-default">
						Next.js 16
					</span>
					<span className="rounded-full bg-neutral-100 border border-neutral-500/20 px-4 py-2 text-sm font-body text-neutral-900 transition-all hover:scale-110 hover:border-accent-600 cursor-default">
						FastAPI + PostgreSQL
					</span>
					<span className="rounded-full bg-neutral-100 border border-neutral-500/20 px-4 py-2 text-sm font-body text-neutral-900 transition-all hover:scale-110 hover:border-accent-600 cursor-default">
						Redis Sessions
					</span>
					<span className="rounded-full bg-accent-400/20 border border-accent-600 px-4 py-2 text-sm font-body text-accent-600 transition-all hover:scale-110 hover:bg-accent-400/30 cursor-default">
						Mistral AI
					</span>
				</div>
			</main>

			{/* Footer */}
			<footer className="mt-16 text-sm font-body text-neutral-500">
				<p>Built for the Mistral AI Internship Application</p>
			</footer>
		</div>
	);
}
