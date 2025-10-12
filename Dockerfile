FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY bot/ ./bot/
COPY data/ ./data/
COPY main.py .

# Ensure cache directories exist in the image (will be volume-mounted in compose)
ENV HF_HOME=/app/storage/huggingface \
    TRANSFORMERS_CACHE=/app/storage/huggingface/transformers \
    HF_DATASETS_CACHE=/app/storage/huggingface/datasets \
    HUGGINGFACE_HUB_CACHE=/app/storage/huggingface/hub \
    XDG_CACHE_HOME=/app/storage/.cache
RUN mkdir -p "$HF_HOME" "$TRANSFORMERS_CACHE" "$HF_DATASETS_CACHE" "$HUGGINGFACE_HUB_CACHE" "$XDG_CACHE_HOME"

# Run the bot
CMD ["python", "main.py"]
