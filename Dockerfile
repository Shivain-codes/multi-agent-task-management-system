FROM python:3.12-slim

# Runtime and pip defaults
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for security
RUN useradd -m -u 1000 nexus
WORKDIR /app

# Install Python dependencies first (layer cache optimisation)
COPY requirements.txt .
RUN python -m pip install --upgrade pip \
    && python -m pip install --prefer-binary -r requirements.txt

# Copy only runtime files
COPY --chown=nexus:nexus app ./app
COPY --chown=nexus:nexus scripts ./scripts

# Create credentials directory (mounted at runtime or via Secret Manager)
RUN mkdir -p /app/credentials && chown nexus:nexus /app/credentials

USER nexus

# Cloud Run uses PORT env var; default 8080
ENV PORT=8080
EXPOSE 8080

# Health check for Cloud Run
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 1 --loop uvloop --http httptools"]
