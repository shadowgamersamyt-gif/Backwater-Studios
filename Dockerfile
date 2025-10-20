# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (including PostgreSQL client libs)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY pyproject.toml uv.lock* ./

# Install uv
RUN pip install --no-cache-dir uv

# Install Python dependencies
RUN uv sync --frozen

# Copy application code
COPY . .

# Expose port for UptimeRobot health checks
EXPOSE 8080

# Run the bot
CMD ["uv", "run", "main.py"]
