# --- Mini App (React/Vite) ---
FROM node:22-slim AS frontend

WORKDIR /frontend
COPY telegram-site/frontend/package.json telegram-site/frontend/package-lock.json ./
RUN npm ci

COPY telegram-site/frontend/ ./
ARG VITE_API_URL=
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

# --- Lumo worker ---
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=frontend /frontend/dist /app/telegram-site/frontend/dist

ENV PYTHONUNBUFFERED=1
ENV LUMO_MODE=worker
ENV AUTO_BUILD_WEBAPP=false
ENV API_ENABLED=true
ENV SKIP_INSTANCE_LOCK=true

EXPOSE 8000

CMD ["python", "main.py"]
