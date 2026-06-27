# --- Lumo API worker (Mini App hosted separately on Vercel) ---
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV LUMO_MODE=worker
ENV AUTO_BUILD_WEBAPP=false
ENV SERVE_MINI_APP=false
ENV API_ENABLED=true
ENV SKIP_INSTANCE_LOCK=true

EXPOSE 8000

CMD ["python", "main.py"]
