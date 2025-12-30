export default function Home() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-b from-slate-900 via-purple-900 to-slate-900 px-4">
      <main className="flex flex-col items-center gap-8 text-center">
        {/* Logo/Title */}
        <div className="flex flex-col items-center gap-4">
          <h1 className="text-6xl font-bold tracking-tight text-white">
            Mistral <span className="text-purple-400">Realms</span>
          </h1>
          <p className="text-xl text-gray-300">
            AI-Powered D&D Adventures
          </p>
        </div>

        {/* Description */}
        <div className="max-w-2xl space-y-4 text-gray-300">
          <p className="text-lg">
            Embark on epic adventures guided by an AI Dungeon Master powered by{" "}
            <span className="font-semibold text-purple-400">Mistral AI</span>.
          </p>
          <p className="text-sm text-gray-400">
            Create your character, make choices, and watch your story unfold in real-time.
          </p>
        </div>

        {/* Coming Soon Badge */}
        <div className="mt-8 rounded-full border border-purple-500/50 bg-purple-500/10 px-6 py-3">
          <p className="text-sm font-medium text-purple-300">
            🚧 Currently in Development
          </p>
        </div>

        {/* Tech Stack Pills */}
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <span className="rounded-full bg-white/10 px-4 py-2 text-sm font-medium text-white">
            Next.js 16
          </span>
          <span className="rounded-full bg-white/10 px-4 py-2 text-sm font-medium text-white">
            TypeScript
          </span>
          <span className="rounded-full bg-white/10 px-4 py-2 text-sm font-medium text-white">
            Tailwind CSS
          </span>
          <span className="rounded-full bg-white/10 px-4 py-2 text-sm font-medium text-white">
            FastAPI
          </span>
          <span className="rounded-full bg-purple-500/20 px-4 py-2 text-sm font-medium text-purple-300">
            Mistral AI
          </span>
        </div>
      </main>

      {/* Footer */}
      <footer className="mt-16 text-sm text-gray-500">
        <p>Built for the Mistral AI Internship Application</p>
      </footer>
    </div>
  );
}
