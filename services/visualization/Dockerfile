# Multi-stage build for Visualization Service
# Build stage
FROM python:3.11-slim as builder

# Install build dependencies including graphics libraries
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    libfreetype6-dev \
    libpng-dev \
    libjpeg-dev \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN pip install --no-cache-dir uv

# Set build directory
WORKDIR /build

# Copy project configuration
COPY pyproject.toml ./
COPY services/visualization/requirements.txt ./

# Create virtual environment and install dependencies
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install -r requirements.txt

# Production stage
FROM python:3.11-slim as production

# Install only runtime dependencies for graphics
RUN apt-get update && apt-get install -y \
    libfreetype6 \
    libpng16-16 \
    libjpeg62-turbo \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set up environment
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/app"
ENV MPLBACKEND=Agg

WORKDIR /app

# Copy shared modules
COPY shared /app/shared

# Copy service code
COPY services/visualization /app

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app && \
    mkdir -p /app/output && \
    mkdir -p /app/database && \
    chown -R app:app /app/output && \
    chown -R app:app /app/database
USER app

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

CMD ["python", "main.py"]
