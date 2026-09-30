FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Install system-level dependencies for document processing
# - tesseract-ocr: OCR engine (optional; gracefully disabled if absent)
# - libglib2.0-0 libsm6 libxext6 libxrender-dev: OpenCV headless dependencies
# - libgl1-mesa-glx: OpenCV dependency
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    tesseract-ocr \
    tesseract-ocr-eng \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies using pip (reproducible via pinned requirements.txt)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code (excludes node_modules, dist, .env, *.db via .dockerignore)
COPY . .

# Create data directories (volumes will be mounted over these at runtime)
RUN mkdir -p data/uploads data/reports

EXPOSE 8000

# Run Alembic migrations then start uvicorn
# Using shell form so env vars are expanded
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
