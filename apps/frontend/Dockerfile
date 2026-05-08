# ── Stage 1: Build ──────────────────────────────────────────────────────────
FROM node:22-alpine AS builder

WORKDIR /frontend

COPY package.json package-lock.json* ./
RUN npm install

# Accept build-time API URL so Vite bakes it into the bundle
ARG VITE_API_BASE_URL=https://job-agent-backend-production-a463.up.railway.app
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

COPY . .
RUN npm run build

# ── Stage 2: Serve with nginx ────────────────────────────────────────────────
FROM nginx:alpine

COPY --from=builder /frontend/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
