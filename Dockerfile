FROM python:3.12-slim

# Cache bust: v2
WORKDIR /app

# System deps for Pillow and image processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "src.app.server:app", "--host", "0.0.0.0", "--port", "8080"]
