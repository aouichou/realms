# Multi-stage build for Next.js frontend

# Stage 1: Dependencies - Install production dependencies only
FROM node:20-alpine AS deps
WORKDIR /app

# Install libc6-compat for alpine compatibility
RUN apk add --no-cache libc6-compat

# Copy package files for better layer caching
COPY package.json package-lock.json* ./

# Install dependencies with clean install
RUN npm ci --only=production --ignore-scripts

# Stage 2: Builder - Build the application
FROM node:20-alpine AS builder
WORKDIR /app

# Install libc6-compat
RUN apk add --no-cache libc6-compat

# Copy package files
COPY package.json package-lock.json* ./

# Install all dependencies (including dev dependencies)
RUN npm ci --ignore-scripts

# Copy source code
COPY . .

# Set production environment variables
ENV NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=production \
    SKIP_ENV_VALIDATION=1

# Build Next.js application with standalone output
RUN npm run build

# Stage 3: Production - Minimal runtime image
FROM node:20-alpine AS runner
WORKDIR /app

# Install minimal runtime dependencies
RUN apk add --no-cache curl

# Create non-root user
RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

# Set production environment
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME="0.0.0.0"

# Copy necessary files from builder (order matters for optimal caching)
COPY --from=builder --chown=nextjs:nodejs /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Switch to non-root user for security
USER nextjs

# Expose port
EXPOSE 3000

# Health check with faster interval
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:3000 || exit 1

# Start the application
CMD ["node", "server.js"]
