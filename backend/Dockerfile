FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (minimal for now)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    gosu \
    && rm -rf /var/lib/apt/lists/*

# Note: We'll use TA-Lib-binary instead of compiling from source
# This is faster and more reliable

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make scripts executable
RUN chmod +x /app/start.sh /app/entrypoint.sh

# Create non-root user
RUN useradd -m -u 1000 quantlab && \
    chown -R quantlab:quantlab /app

# Don't switch user here - entrypoint will handle it
# USER quantlab

# Expose port
EXPOSE 8000

# Use entrypoint to fix permissions before running start.sh
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["/app/start.sh"]
