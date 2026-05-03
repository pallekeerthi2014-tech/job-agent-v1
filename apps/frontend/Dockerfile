FROM node:22-alpine

WORKDIR /frontend

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

CMD ["sh", "-c", "npm run preview -- --host 0.0.0.0 --port ${PORT:-${FRONTEND_PORT:-5173}}"]
