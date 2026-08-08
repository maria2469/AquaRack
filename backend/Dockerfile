FROM python:3.11-slim

WORKDIR /app

# Install CA certificates
RUN apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates && \
    update-ca-certificates && \
    mkdir -p /root/.postgresql && \
    mkdir -p /app/certs && \
    rm -rf /var/lib/apt/lists/*

# Copy CockroachDB Cloud CA certificate to both locations for compatibility
COPY root.crt /root/.postgresql/root.crt
COPY root.crt /app/certs/root.crt

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

ENV PYTHONUNBUFFERED=1
ENV PORT=8000

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]