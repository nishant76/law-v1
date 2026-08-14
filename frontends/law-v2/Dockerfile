# ── Stage 1: Build ──────────────────────────────────────────────────────────
FROM oven/bun:1 AS builder
WORKDIR /app

COPY package.json bun.lock ./
RUN bun install --frozen-lockfile

COPY . .

# Build args — VITE_API_URL is baked into client bundles at build time
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# Build the app (produces dist/client + dist/server)
RUN bun run build

# Bundle the SSR server into a single self-contained file.
# The Vite SSR build externalises React/TanStack (cloudflare target).
# esbuild re-bundles them from node_modules so the runtime image needs zero deps.
# Use bun's built-in bundler (bun binary is linux/amd64 in this builder — no arch mismatch)
RUN bun build dist/server/server.js \
      --target=node \
      --format=esm \
      --outfile=dist/server.bundle.mjs \
      --external="node:*"

# ── Stage 2: Run ────────────────────────────────────────────────────────────
# Node.js 20 — has Web Fetch API (Request/Response) built-in.
# No node_modules needed: everything is in dist/server.bundle.mjs.
FROM node:20-slim
WORKDIR /app

COPY --from=builder /app/dist ./dist
COPY --from=builder /app/serve.mjs ./serve.mjs

ENV PORT=8080
ENV HOST=0.0.0.0

EXPOSE 8080

CMD ["node", "serve.mjs"]
