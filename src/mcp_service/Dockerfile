# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install any production dependencies
COPY src/mcp_service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy proto files and generate protobuf
COPY protos/ /protos/
COPY src/mcp_service/genproto.sh .
RUN chmod +x genproto.sh && ./genproto.sh

# Copy the application files into the container at /app
COPY src/mcp_service/main.py .

# Expose the port the app runs on
ENV HTTP_PORT 8080
EXPOSE ${HTTP_PORT}

# Datadog APM Configuration
ENV DD_SERVICE=mcp-service
ENV DD_ENV=hackathon
ENV DD_VERSION=1.0.0
ENV DD_TRACE_ENABLED=true
ENV DD_LOGS_INJECTION=true

# Run the application
CMD exec ddtrace-run python main.py
