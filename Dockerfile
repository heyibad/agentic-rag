# 1. Use the distroless uv image to get uv & uvx binaries
FROM ghcr.io/astral-sh/uv:debian-slim AS uv-binaries

# Install system deps
RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*

# Copy uv & uvx into PATH
COPY --from=uv-binaries /uv /uvx /usr/local/bin/  
# Create a non-root user
RUN useradd -m -u 1000 user
USER user

# Set up environment
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:/usr/local/bin:/app/.venv/bin:$PATH \
    PORT=7860 \
    CHAINLIT_HOST=0.0.0.0 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copy in only pyproject and lock first (for caching)
COPY --chown=user:user pyproject.toml uv.lock ./

# Install Python dependencies reproducibly
RUN uv sync --locked --no-cache && \
    rm -rf /root/.cache/uv                             

# Copy the rest of your application
COPY --chown=user:user . .

# Expose the port that Chainlit uses
EXPOSE 7860

# Launch Chainlit via the uv-managed environment
CMD ["chainlit", "run", "main.py", "--host", "0.0.0.0", "--port", "7860"]
