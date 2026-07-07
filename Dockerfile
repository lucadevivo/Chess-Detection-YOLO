FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        stockfish libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# torch + torchvision CPU-only insieme (evita il mismatch torchvision::nms)
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

COPY web/requirements.txt /app/web/requirements.txt
RUN pip install --no-cache-dir -r /app/web/requirements.txt

COPY src/ /app/src/
COPY web/ /app/web/
COPY pezzi/ /app/pezzi/
COPY best.pt /app/best.pt

EXPOSE 8000
CMD ["uvicorn", "web.app:app", "--host", "0.0.0.0", "--port", "8000"]
