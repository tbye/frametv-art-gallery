# ---------- Frontend ----------
FROM node:20-slim AS frontend

WORKDIR /frontend

COPY frontend/package.json frontend/package-lock.json ./
# package.json pins @react-router/serve@8 while the rest of the stack is 7.x
RUN npm ci --legacy-peer-deps

COPY frontend/ ./

ARG VITE_APP_VERSION=dev
ENV VITE_APP_VERSION=$VITE_APP_VERSION

RUN npm run build


# ---------- Python builder ----------
FROM python:3.13-slim AS builder

# Install git only for dependency build
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./

COPY . .

# Upgrade pip and install dependencies into custom prefix
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --prefix=/install .


# ---------- Runtime ----------
FROM python:3.13-slim

WORKDIR /app

# Copy installed packages
COPY --from=builder /install /usr/local

# Copy app code
COPY . .

# Overlay production frontend build (Flask serves frontend/build/client)
COPY --from=frontend /frontend/build ./frontend/build

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
# Run entrypoint.sh for db migrations, ..
ENTRYPOINT ["/entrypoint.sh"]

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:8000"]
