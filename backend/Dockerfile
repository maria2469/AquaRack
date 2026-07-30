FROM python:3.11-slim

WORKDIR /app

# Install CA certificates
RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates && \
    update-ca-certificates && \
    mkdir -p /root/.postgresql && \
    rm -rf /var/lib/apt/lists/*

# Copy CockroachDB Cloud CA certificate
COPY certs/root.crt /root/.postgresql/root.crt

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["python", "run.py", "--host", "0.0.0.0"]