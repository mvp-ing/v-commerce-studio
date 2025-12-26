FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends wget curl \
    && rm -rf /var/lib/apt/lists/*

COPY src/observability_insights_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/observability_insights_service/ .

RUN groupadd -r insights && useradd -r -g insights insights
RUN chown -R insights:insights /app
USER insights

EXPOSE 8080

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DD_SERVICE=observability-insights-service
ENV DD_ENV=hackathon
ENV DD_TRACE_ENABLED=1
ENV DD_LOGS_INJECTION=true
ENV HTTP_PORT=8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

CMD ["python", "main.py"]
