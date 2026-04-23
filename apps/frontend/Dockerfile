FROM node:22-alpine

WORKDIR /frontend

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

CMD ["sh", "-c", "npm run dev -- --host 0.0.0.0 --port ${FRONTEND_PORT:-5173}"]
