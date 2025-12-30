# Mistral Realms Frontend

AI-Powered D&D Adventure Generator - Next.js Frontend

## 🚀 Quick Start

### Local Development

1. **Install dependencies**
```bash
npm install
```

2. **Configure environment**
```bash
cp .env.local.example .env.local
# Edit .env.local if needed (defaults work with docker-compose)
```

3. **Run the dev server**
```bash
npm run dev
```

4. **Open in browser**
- http://localhost:3000

### Production Build

```bash
# Build for production
npm run build

# Start production server
npm run start
```

## 📁 Project Structure

```
frontend/
├── app/
│   ├── layout.tsx          # Root layout with metadata
│   ├── page.tsx            # Home page
│   ├── globals.css         # Global styles
│   └── chat/               # Chat interface (coming soon)
├── components/             # Reusable components (coming soon)
├── lib/                   # Utilities and helpers (coming soon)
├── public/                # Static assets
├── .env.local.example     # Environment template
├── next.config.ts         # Next.js configuration
├── tailwind.config.ts     # Tailwind CSS configuration
└── tsconfig.json          # TypeScript configuration
```

## 🛠️ Tech Stack

- **Framework**: Next.js 16 with App Router
- **Language**: TypeScript 5
- **Styling**: Tailwind CSS v4
- **Fonts**: Geist Sans & Geist Mono
- **Linting**: ESLint with Next.js config
- **Compiler**: React Compiler (enabled)
- **Bundler**: Turbopack

## 🎨 Features

- Server-side rendering with App Router
- TypeScript for type safety
- Tailwind CSS for styling
- Optimized font loading with next/font
- ESLint for code quality
- React Compiler for automatic optimizations

## 📝 Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | `http://localhost:8000` |

## 🧪 Development

```bash
# Run dev server with turbopack
npm run dev

# Run linter
npm run lint

# Build for production
npm run build
```

## 🐳 Docker (Coming Soon)

Docker support will be added in RL-12.

