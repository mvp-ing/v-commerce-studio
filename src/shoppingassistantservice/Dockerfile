 

FROM --platform=$BUILDPLATFORM python:3.12.8-slim@sha256:123be5684f39d8476e64f47a5fddf38f5e9d839baff5c023c815ae5bdfae0df7 AS base

FROM base AS builder

RUN apt-get -qq update \
    && apt-get install -y --no-install-recommends g++ \
    && rm -rf /var/lib/apt/lists/*

# get packages
COPY requirements.txt .
RUN pip install -r requirements.txt

FROM base
# Enable unbuffered logging
ENV PYTHONUNBUFFERED=1

# get packages
WORKDIR /shoppingassistantservice

# Grab packages from builder
COPY --from=builder /usr/local/lib/python3.12/ /usr/local/lib/python3.12/

# Add the application
COPY . .

# set listen port
ENV PORT "8080"
EXPOSE 8080

# Datadog LLM Observability environment variables (agentless mode)
ENV DD_LLMOBS_ENABLED=1
ENV DD_LLMOBS_AGENTLESS_ENABLED=1
ENV DD_LLMOBS_ML_APP=v-commerce-shopping-assistant
ENV DD_SERVICE=shoppingassistantservice
ENV DD_ENV=hackathon
ENV DD_TRACE_ENABLED=1
ENV DD_LOGS_INJECTION=true

ENTRYPOINT ["python", "shoppingassistantservice.py"]
