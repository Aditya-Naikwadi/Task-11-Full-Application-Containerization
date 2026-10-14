# ============================================================================
# Stage: Backend Deep Learning REST API (Flask + TensorFlow)
# Base Image: Lightweight Debian-based Python 3.10 runtime
# ============================================================================
FROM python:3.10-slim

# Prevent Python from writing bytecode (.pyc) and enforce unbuffered console logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5000

# Set container working directory
WORKDIR /app

# Install runtime system utilities (curl for container health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Optimize layer caching: Install dependencies before copying application code
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application source files and pre-trained deep learning model (model.h5)
COPY . .

# Expose backend REST API port
EXPOSE 5000

# Define container health check to monitor service readiness
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Execute Flask application (bound to 0.0.0.0 to listen on all container interfaces)
CMD ["python", "app.py"]
