FROM python:3.13-slim

# Install system dependencies and uv as root
RUN apt-get update && \
    apt-get install -y curl && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/ && \
    mv /root/.local/bin/uvx /usr/local/bin/ && \
    mkdir -p /.cache/uv && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 user && \
    chown -R user:user /.cache/uv

# Switch to non-root user
USER user

# Set up environment
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:/usr/local/bin:$PATH \
    PORT=7860 \
    CHAINLIT_HOST=0.0.0.0 \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR $HOME/app

# Copy all application files with correct ownership
COPY --chown=user:user . .

# Install dependencies as the non-root user
RUN uv sync

# Expose the port
EXPOSE 7860

# Run the application using uv run
CMD ["uv", "run", "chainlit", "run", "ui/app.py", "--host", "0.0.0.0", "--port", "7860"]