# Use lightweight official Python image
FROM python:3.10-slim

# Set working directory inside container
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=UTC

# Install system dependencies (tzdata for timezone support)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files and directories
COPY . /app

# Expose Web Dashboard Port
EXPOSE 5000

# Command to run Web Dashboard App & Background Daemon Thread
CMD ["python", "app.py"]
