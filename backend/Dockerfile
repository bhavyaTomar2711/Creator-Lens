# Backend image for Hugging Face Spaces (Docker SDK). Build context = backend/.
FROM python:3.11-slim

# ffmpeg for yt-dlp audio extraction; clean apt cache to keep image small.
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model so the first request isn't slow (no cold-start fetch).
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5')"

COPY . .

# HF Spaces routes traffic to port 7860.
ENV PORT=7860
EXPOSE 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
