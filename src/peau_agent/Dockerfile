# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install any production dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

# Expose the port the app runs on
ENV HTTP_PORT 8080
EXPOSE ${HTTP_PORT}

# Datadog LLM Observability environment variables (agentless mode)
ENV DD_LLMOBS_ENABLED=1
ENV DD_LLMOBS_AGENTLESS_ENABLED=1
ENV DD_LLMOBS_ML_APP=v-commerce-peau-agent
ENV DD_SERVICE=peau-agent
ENV DD_ENV=hackathon
ENV DD_TRACE_ENABLED=1
ENV DD_LOGS_INJECTION=true

# Run the application
CMD exec python mcp_server.py
