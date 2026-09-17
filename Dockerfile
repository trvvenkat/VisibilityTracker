FROM python:3.11-slim

WORKDIR /app

# Ensure output is streamed in real time without buffering
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    BROWSER_HEADLESS=true

# Install basic system utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium and its required OS dependencies
RUN playwright install --with-deps chromium

# Copy application source code
COPY . .

# Ensure data directories exist
RUN mkdir -p /app/data/uploads /app/data/jobs

EXPOSE 8000

# Start Uvicorn with reverse-proxy header support for ngrok
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
