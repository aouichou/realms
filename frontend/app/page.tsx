import Link from "next/link";

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4">
      <main className="flex flex-col items-center gap-8 text-center max-w-4xl">
        {/* Logo/Title */}
        <div className="flex flex-col items-center gap-4">
          <h1 className="text-6xl md:text-7xl font-display text-primary-900">
            Mistral Realms
          </h1>
          <p className="text-xl font-body text-neutral-500">
            AI-Powered D&D Adventures
          </p>
        </div>

        {/* Description */}
        <div className="max-w-2xl space-y-4 font-body text-narrative">
          <p className="text-primary-900">
            Embark on epic adventures guided by an AI Dungeon Master powered by{" "}
            <span className="font-semibold text-accent-600">Mistral AI</span>.
          </p>
          <p className="text-neutral-500">
            Create your character, make choices, and watch your story unfold in real-time with true randomness for dice rolls.
          </p>
        </div>

        {/* CTA Buttons */}
        <div className="mt-8 flex gap-4 flex-wrap justify-center">
          <Link
            href="/character/create"
            className="inline-flex items-center gap-2 rounded-lg bg-primary-900 px-8 py-4 text-lg font-body font-semibold text-white transition-all hover:bg-accent-600 hover:scale-105 shadow-lg"
          >
            Create Character
            <svg
              className="h-5 w-5"
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
            href="/game/1"
            className="inline-flex items-center gap-2 rounded-lg bg-secondary-600 px-8 py-4 text-lg font-body font-semibold text-white transition-all hover:bg-accent-400 hover:text-primary-900 shadow-lg"
          >
            Continue Adventure
          </Link>
        </div>

        {/* Features */}
        <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-6 w-full">
          <div className="p-6 bg-neutral-100 rounded-lg border border-neutral-500/20">
            <div className="text-3xl mb-3">⚔️</div>
            <h3 className="font-display text-xl text-primary-900 mb-2">12 D&D Classes</h3>
            <p className="text-sm font-body text-neutral-500">
              Choose from Barbarian, Bard, Cleric, Druid, Fighter, Monk, Paladin, Ranger, Rogue, Sorcerer, Warlock, or Wizard
            </p>
          </div>
          
          <div className="p-6 bg-neutral-100 rounded-lg border border-neutral-500/20">
            <div className="text-3xl mb-3">🎲</div>
            <h3 className="font-display text-xl text-primary-900 mb-2">True Randomness</h3>
            <p className="text-sm font-body text-neutral-500">
              Dice rolls powered by Random.org's atmospheric noise for genuine unpredictability
            </p>
          </div>
          
          <div className="p-6 bg-neutral-100 rounded-lg border border-neutral-500/20">
            <div className="text-3xl mb-3">🤖</div>
            <h3 className="font-display text-xl text-primary-900 mb-2">AI Dungeon Master</h3>
            <p className="text-sm font-body text-neutral-500">
              Mistral AI creates dynamic narratives, generates scene images, and responds to your choices
            </p>
          </div>
        </div>

        {/* Tech Stack Pills */}
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <span className="rounded-full bg-neutral-100 border border-neutral-500/20 px-4 py-2 text-sm font-body text-neutral-900">
            Next.js 16
          </span>
          <span className="rounded-full bg-neutral-100 border border-neutral-500/20 px-4 py-2 text-sm font-body text-neutral-900">
            FastAPI + PostgreSQL
          </span>
          <span className="rounded-full bg-neutral-100 border border-neutral-500/20 px-4 py-2 text-sm font-body text-neutral-900">
            Redis Sessions
          </span>
          <span className="rounded-full bg-accent-400/20 border border-accent-600 px-4 py-2 text-sm font-body text-accent-600">
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

