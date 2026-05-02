FROM node:22-alpine

WORKDIR /frontend

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

ARG VITE_API_BASE_URL=https://gmail-analytics-backend-41411095034.us-central1.run.app
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

CMD ["sh", "-c", "npm run preview -- --host 0.0.0.0 --port ${PORT:-8080}"]
