# Multi-stage build for FIT File Mapper development container
# Build stage - includes all build tools and dependencies
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    wget \
    build-essential \
    libgdal-dev \
    gdal-bin \
    libspatialindex-dev \
    libproj-dev \
    libgeos-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager
RUN pip install --no-cache-dir uv

# Set working directory for build
WORKDIR /build

# Copy project configuration
COPY pyproject.toml .

# Create virtual environment and install dependencies
RUN uv venv /opt/venv && \
    /opt/venv/bin/uv pip install -e ".[dev,all]"

# Production stage - minimal runtime dependencies
FROM python:3.11-slim as production

# Install only runtime dependencies
RUN apt-get update && apt-get install -y \
    libgdal32 \
    libspatialindex6 \
    libproj25 \
    libgeos-c1v5 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create vscode user
RUN groupadd --gid 1000 vscode \
    && useradd --uid 1000 --gid vscode --shell /bin/bash --create-home vscode

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set up environment
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/workspace"

# Set working directory
WORKDIR /workspace

# Set user
USER vscode

# Default command
CMD ["sleep", "infinity"]
