# ============================================================================
# Stage: Frontend Dashboard (Streamlit UI)
# Base Image: Lightweight Debian-based Python 3.10 runtime
# ============================================================================
FROM python:3.10-slim

# Prevent Python bytecode generation and configure Streamlit headless environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Set container working directory
WORKDIR /app

# Install minimal system dependencies for container diagnostics
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Optimize layer caching: Install Python dependencies independently
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy frontend application code and static assets
COPY . .

# Expose Streamlit default UI port
EXPOSE 8501

# Define container health check for Streamlit core status
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Launch Streamlit server explicitly bound to 0.0.0.0 and port 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
