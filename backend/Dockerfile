FROM python:3.11-slim

WORKDIR /app

# Install required packages and download the CockroachDB Cloud CA certificate
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    ca-certificates && \
    mkdir -p /root/.postgresql && \
    curl -fsSL \
    https://cockroachlabs.cloud/clusters/70280767-44c2-49ab-89fc-baa523747fa3/cert \
    -o /root/.postgresql/root.crt && \
    ls -l /root/.postgresql && \
    head -3 /root/.postgresql/root.crt && \
    apt-get purge -y --auto-remove curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["python", "run.py", "--host", "0.0.0.0"]