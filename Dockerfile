# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \ 
    libpq-dev \ 
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first (for caching)
COPY pyproject.toml uv.lock* ./

# Install uv
RUN pip install --no-cache-dir uv

# Install Python dependencies (no dev deps)
RUN uv sync --frozen --no-dev

# Copy the rest of the project
COPY . .

# Expose port 8080 for aiohttp (UptimeRobot)
EXPOSE 8080

# Set environment variables (production safe defaults)
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Start the Discord bot (which also starts aiohttp keep-alive server)
CMD ["uv", "run", "main.py"]
