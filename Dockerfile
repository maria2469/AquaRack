# AquaMind AI — shared base image for Phase 1 and every Phase 2 microservice
# (SDD Phase 1, Section 19: "packaged as a Docker image usable both for local
# `docker run` and as the base image for the Phase 2 microservices, minimising
# drift between phases").
#
# The CMD below runs the combined Phase 1+2 gateway by default. Individual
# Phase 2 microservices override CMD (see docker-compose.yml) to run just
# their own service module instead.

FROM python:3.11-slim

WORKDIR /app

COPY phase1_standalone/requirements.txt ./phase1_requirements.txt
COPY phase2_distributed/requirements.txt ./phase2_requirements.txt
RUN pip install --no-cache-dir -r phase1_requirements.txt -r phase2_requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app:/app/phase1_standalone"

EXPOSE 8000

CMD ["python", "run_phase2.py", "--host", "0.0.0.0"]
