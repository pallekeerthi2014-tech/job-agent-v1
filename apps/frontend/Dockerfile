# Builder stage
FROM node:22-alpine AS builder

WORKDIR /frontend

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

RUN npm run build

# Production stage
FROM node:22-alpine

WORKDIR /frontend

RUN npm install -g serve

COPY --from=builder /frontend/dist ./dist

EXPOSE 5173

CMD ["serve", "-s", "dist", "-l", "5173"]
