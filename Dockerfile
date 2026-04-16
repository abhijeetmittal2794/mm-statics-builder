FROM python:3.12-slim

WORKDIR /app

# System deps for Pillow, rembg, onnxruntime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=8080
EXPOSE 8080

CMD ["uvicorn", "src.app.server:app", "--host", "0.0.0.0", "--port", "8080"]
