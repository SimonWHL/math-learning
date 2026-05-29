# Stage 1: Build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --registry https://registry.npmmirror.com
COPY frontend/ .
RUN npm run build

# Stage 2: Python app
FROM python:3.12-slim
WORKDIR /app

# System dependencies for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx libglib2.0-0 libsm6 libxext6 libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir . --index-url https://mirrors.aliyun.com/pypi/simple/

# Copy source code
COPY src/ src/

# Copy frontend build
COPY --from=frontend-build /app/frontend/dist frontend/dist

# Expose port
EXPOSE 8000

# Run with uvicorn
CMD ["uvicorn", "math_learning.web.main:app", "--host", "0.0.0.0", "--port", "8000"]
