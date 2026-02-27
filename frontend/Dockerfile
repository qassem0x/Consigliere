# ── Stage 1: Build ──────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts

COPY . .

# VITE_API_URL is injected at build time.
# In Docker (behind Nginx), it becomes an empty string so calls go to /api/...
# In local dev it falls back to http://localhost:8000 in the source code.
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# ── Stage 2: Serve ───────────────────────────────────────────────────────────
FROM nginx:1.27-alpine

# Remove default nginx page
RUN rm -rf /usr/share/nginx/html/*

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# nginx config is mounted via docker-compose from the root nginx.conf
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
