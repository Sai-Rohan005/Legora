# ==========================================================
# Base Image
# ==========================================================
FROM python:3.11-slim

# Prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1

# Print logs immediately
#this is important for Docker logs to be visible in real-time
ENV PYTHONUNBUFFERED=1

# Hugging Face cache location
ENV HF_HOME=/app/.cache/huggingface
ENV TRANSFORMERS_CACHE=/app/.cache/huggingface
ENV SENTENCE_TRANSFORMERS_HOME=/app/.cache/huggingface

# Streamlit
ENV STREAMLIT_SERVER_PORT=7860
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# ==========================================================
# System Dependencies
# ==========================================================
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    poppler-utils \
    tesseract-ocr \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# ==========================================================
# Working Directory
# ==========================================================
WORKDIR /app

# ==========================================================
# Install Python Packages
# ==========================================================
COPY requirements.txt .

# CPU wheels avoid pulling CUDA runtime libraries into the local deployment.
RUN pip install --no-cache-dir torch==2.12.0 --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

# ==========================================================
# Copy Project
# ==========================================================
COPY . .

# ==========================================================
# Expose Streamlit Port
# ==========================================================
EXPOSE 8000 7860

# ==========================================================
# Launch Streamlit
# ==========================================================
CMD ["python", "-m", "uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
