FROM python:3.11-slim

WORKDIR /app

# Install CA certificates
RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates && \
    update-ca-certificates && \
    mkdir -p /root/.postgresql && \
    rm -rf /var/lib/apt/lists/*

# Copy CockroachDB Cloud CA certificate
COPY root.crt /root/.postgresql/root.crt

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["python", "run.py", "--host", "0.0.0.0"]