# ---------- Frontend ----------
# Bootstrap with a minimal image; pnpm installs the latest stable (LTS) Node runtime.
# Project deps still use npm + package-lock.json (existing package management).
FROM debian:bookworm-slim AS frontend

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        # Required by the standalone pnpm binary
        libatomic1 \
    && rm -rf /var/lib/apt/lists/*

# Standalone pnpm (does not require Node preinstalled)
ENV PNPM_HOME=/pnpm
# Installer places the CLI in $PNPM_HOME/bin
ENV PATH=$PNPM_HOME/bin:$PATH
RUN curl -fsSL https://get.pnpm.io/install.sh | SHELL=bash PNPM_HOME=$PNPM_HOME sh - \
    && pnpm --version

# Latest stable Node = Active LTS via pnpm runtime (`pnpm env` is deprecated)
# pnpm v11+ does not ship npm with the Node runtime — install npm separately.
RUN pnpm runtime set node lts -g \
    && pnpm add -g npm \
    && node --version \
    && npm --version

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
