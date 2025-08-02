# Production Dockerfile for Agentic AI Config Manager
FROM python:3.11-slim

# Set workdir
WORKDIR /app

# Install system dependencies (if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Expose the port (change if needed)
EXPOSE 8000

# Set environment variables for production
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Start the FastAPI app with multiple workers
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--log-level", "info"]
