# Multi-stage build for API Gateway
# Build stage
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN pip install --no-cache-dir uv

# Set build directory
WORKDIR /build

# Copy project configuration
COPY pyproject.toml ./
COPY services/api-gateway/requirements.txt ./

# Create virtual environment and install dependencies
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set up environment
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/app"

WORKDIR /app

# Copy shared modules
COPY shared /app/shared

# Copy service code
COPY services/api-gateway /app

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app && \
    mkdir -p /app/database && \
    chown -R app:app /app/database
USER app

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/health')" || exit 1

CMD ["python", "main.py"]
