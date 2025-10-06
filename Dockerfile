FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY bot/ ./bot/
COPY data/ ./data/
COPY main.py .

# Run the bot
CMD ["python", "main.py"]
