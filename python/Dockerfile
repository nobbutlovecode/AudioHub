FROM python: 3.10-slim

WORKDIR /workspace

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . . 

CMD ["sh", "-c", "uvicorn server.main:api_service --host 0.0.0.0 --port ${PORT: -8000}"]