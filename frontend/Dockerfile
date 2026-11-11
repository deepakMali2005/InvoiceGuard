FROM node:20-slim

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

COPY frontend /app

ENV NEXT_PUBLIC_API_BASE=http://localhost:8000

EXPOSE 3000

CMD ["npm", "run", "dev"]
