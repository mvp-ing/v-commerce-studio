 

FROM python:3.11-slim

# Set working directory
WORKDIR /chatbotservice

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        wget \
        git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY src/chatbotservice/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy proto files and generate protobuf
COPY protos/ /protos/
COPY src/chatbotservice/genproto.sh .
RUN chmod +x genproto.sh && ./genproto.sh

# Copy application code
COPY src/chatbotservice/ .

# Create non-root user for security
RUN groupadd -r chatbot && useradd -r -g chatbot chatbot
RUN chown -R chatbot:chatbot /chatbotservice
USER chatbot

# Expose ports
EXPOSE 8080 8081

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Datadog LLM Observability environment variables (agentless mode)
ENV DD_LLMOBS_ENABLED=1
ENV DD_LLMOBS_AGENTLESS_ENABLED=1
ENV DD_LLMOBS_ML_APP=v-commerce-chatbot
ENV DD_SERVICE=chatbotservice
ENV DD_ENV=hackathon
ENV DD_TRACE_ENABLED=1
ENV DD_LOGS_INJECTION=true

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

# Run the application
CMD ["python", "chatbot_server.py"] 