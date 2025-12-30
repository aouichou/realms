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

## 🐳 Docker

### Development with Hot Reload

**Build development image**
```bash
docker build -f Dockerfile.dev -t mistral-realms-frontend:dev .
```

**Run development container**
```bash
# With environment file
docker run -d -p 3000:3000 \
  -v $(pwd):/app \
  -v /app/node_modules \
  -v /app/.next \
  --env-file .env.local \
  --name realms-frontend-dev \
  mistral-realms-frontend:dev

# Or with environment variable
docker run -d -p 3000:3000 \
  -v $(pwd):/app \
  -v /app/node_modules \
  -v /app/.next \
  -e NEXT_PUBLIC_API_URL=http://backend:8000 \
  --name realms-frontend-dev \
  mistral-realms-frontend:dev
```

### Production Build

**Build production image**
```bash
docker build -t mistral-realms-frontend:latest .
```

**Run production container**
```bash
# With environment variable
docker run -d -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=http://backend:8000 \
  --name realms-frontend \
  mistral-realms-frontend:latest

# Or with environment file
docker run -d -p 3000:3000 \
  --env-file .env.local \
  --name realms-frontend \
  mistral-realms-frontend:latest
```

**View logs**
```bash
docker logs -f realms-frontend
```

**Stop and remove**
```bash
docker stop realms-frontend
docker rm realms-frontend
```

### Docker Features

- **Multi-stage build**: Optimized for production with minimal image size
- **Non-root user**: Security-hardened with dedicated nextjs user
- **Standalone output**: Self-contained build for better portability
- **Health checks**: Built-in health monitoring
- **Hot reload**: Development image supports live code changes

