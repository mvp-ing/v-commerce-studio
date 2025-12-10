---
name: Datadog LLM Observability Hackathon
overview: Implement end-to-end Datadog observability for the v-commerce LLM application, including a new AI-powered Observability Insights Service that predicts errors and suggests cost optimizations using Gemini, with telemetry streaming to Datadog dashboards and automated incident management.
todos:
  - id: phase1-setup
    content: "Phase 1: Set up Datadog Agent locally + instrument chatbotservice, peau_agent, shoppingassistantservice with ddtrace"
    status: pending
  - id: phase2-insights-service
    content: "Phase 2: Create new observability_insights_service with Gemini-powered error prediction and cost optimization"
    status: pending
  - id: phase3-detection-rules
    content: "Phase 3: Configure 3 Datadog detection rules (latency anomaly, cost spike, error rate)"
    status: pending
  - id: phase4-dashboard
    content: "Phase 4: Build Datadog dashboard with health overview, LLM metrics, AI insights panels"
    status: pending
  - id: phase5-incidents
    content: "Phase 5: Set up incident/case management with runbooks and contextual alerts"
    status: pending
  - id: gke-deploy
    content: "Phase 6: Deploy to GKE with Datadog Agent DaemonSet and verify end-to-end"
    status: pending
---

# Datadog LLM Observability Implementation Plan

## Overview

Integrate Datadog observability into the v-commerce microservices application, focusing on the LLM-powered services (chatbotservice, peau_agent, shoppingassistantservice). Create a new **Observability Insights Service** that uses Gemini to analyze telemetry data, predict future errors, and suggest cost-saving methods.

## Target LLM Services (Already Using Vertex AI/Gemini)

- `src/chatbotservice/chatbot_server.py` - Gemini 2.0 Flash
- `src/peau_agent/peau_agent.py` - Gemini 2.0 Flash via ADK
- `src/shoppingassistantservice/shoppingassistantservice.py` - Gemini 1.5 Flash

---

## Phase 1: Datadog Agent Setup and Full-Stack APM Instrumentation

### 1.1 Local Testing Setup

- Deploy Datadog Agent locally via Docker for testing
- Configure `DD_API_KEY`, `DD_SITE`, and `DD_ENV` environment variables
- Enable APM, logs, LLM Observability, and infrastructure monitoring

### 1.2 Instrument ALL Python Services with `ddtrace`

**LLM Services (Primary Focus - Deep Instrumentation):**

| Service | LLM Integration | Special Instrumentation |

|---------|-----------------|------------------------|

| `chatbotservice` | Gemini 2.0 Flash | Token tracking, RAG latency, streaming metrics |

| `peau_agent` | Gemini 2.0 Flash (ADK) | Agent tool calls, behavior analysis latency |

| `shoppingassistantservice` | Gemini 1.5 Flash | LangChain spans, vector search latency |

**Supporting Python Services (Standard APM):**

| Service | Key Metrics |

|---------|-------------|

| `adservice` | Ad serving latency, category match rate |

| `cartservice` | Cart operations, Redis latency |

| `emailservice` | Email delivery success, template rendering |

| `recommendationservice` | Recommendation latency, cache hit rate |

| `tryonservice` | Image processing time, model inference |

| `video_generation` | Video generation duration, queue depth |

| `mcp_service` | Tool call latency, request throughput |

### 1.3 Instrument Go Services with `dd-trace-go`

| Service | Key Metrics |

|---------|-------------|

| `frontend` | HTTP request latency, template rendering, upstream service calls |

| `checkoutservice` | Checkout duration, payment processing, order success rate |

| `productcatalogservice` | Product query latency, search performance |

| `shippingservice` | Quote calculation time, tracking requests |

### 1.4 Instrument Node.js Services with `dd-trace-js`

| Service | Key Metrics |

|---------|-------------|

| `currencyservice` | Conversion latency, API call rate |

| `paymentservice` | Transaction success rate, fraud check latency |

### 1.5 Unified Logging Strategy

- Structured JSON logs from all services
- Correlation IDs (trace_id, span_id) in all log entries
- Log levels: ERROR, WARN, INFO, DEBUG
- Automatic log-to-trace correlation in Datadog

---

## Phase 2: New Observability Insights Service

### 2.1 Create `src/observability_insights_service/`

```
src/observability_insights_service/
├── main.py              # Flask server with scheduled jobs
├── insights_generator.py # Gemini-powered analysis
├── datadog_client.py    # Fetch metrics from Datadog API
├── alert_sender.py      # Send custom events/alerts to Datadog
├── Dockerfile
└── requirements.txt
```

### 2.2 Core Features

**Error Prediction:**

- Fetch historical error patterns from Datadog Metrics API
- Use Gemini to analyze trends and predict potential failures
- Generate actionable alerts with context

**Cost Optimization:**

- Track token usage across all LLM services
- Calculate costs per service/endpoint
- Use Gemini to suggest optimization strategies (caching, prompt engineering, model selection)

**Health Insights:**

- Aggregate signals: latency p99, error rate, throughput
- Generate natural language summaries for dashboard widgets

### 2.3 Implementation Pattern

```python
# insights_generator.py
class ObservabilityInsightsGenerator:
    def __init__(self):
        self.model = GenerativeModel("gemini-2.0-flash")
        self.dd_client = DatadogMetricsClient()
    
    def predict_errors(self, time_window="1h"):
        # Fetch error metrics from Datadog
        # Analyze with Gemini
        # Return predictions with confidence scores
    
    def suggest_cost_savings(self):
        # Fetch token usage metrics
        # Analyze spending patterns
        # Generate recommendations
```

---

## Observability Strategy & Innovation

### Why This Approach is Different

Traditional observability focuses on **reactive monitoring** (errors happened → alert). Our strategy implements **predictive AI-native observability**:

1. **AI Observing AI** - Using Gemini to analyze patterns in LLM telemetry that humans would miss
2. **Business-Correlated Metrics** - Tying LLM performance directly to revenue/conversion impact
3. **Self-Healing Insights** - Not just alerting, but generating actionable remediation steps

### Thought Process Behind Detection Rules

For an e-commerce LLM application, we care about:

- **User Experience** - Is the chatbot actually helping customers?
- **Cost Efficiency** - Are we spending tokens wisely?
- **Security** - Is the LLM being exploited or leaking data?
- **Reliability** - Will the system fail before peak traffic?

---

## Phase 3: Detection Rules (5 Innovative Rules)

### Rule 1: Hallucination Detection (Product Recommendation Accuracy)

**Innovation:** Detects when LLM recommends products that don't exist in catalog

- **Signal:** Custom metric `llm.recommendation.invalid_product_rate`
- **Implementation:** Cross-reference product IDs in LLM responses against ProductCatalogService
- **Trigger:** Invalid product rate > 2% over 10 minutes
- **Severity:** High (directly impacts user trust and potential revenue loss)
- **Action:** Create incident with:
  - Sample hallucinated responses
  - Prompt patterns that caused hallucination
  - Suggested prompt engineering fixes
- **Runbook:** Check RAG corpus freshness, verify product catalog sync, review recent prompt changes

### Rule 2: Prompt Injection / Adversarial Input Detection

**Innovation:** Security-focused rule detecting potential LLM exploitation attempts

- **Signal:** Custom metric `llm.security.injection_attempt_score`
- **Implementation:** Score incoming prompts for injection patterns (jailbreak attempts, system prompt extraction, SQL-like patterns)
- **Trigger:** Injection score > 0.7 OR > 5 suspicious requests from same session in 1 minute
- **Severity:** Critical (security risk)
- **Action:** 
  - Immediate alert to security channel
  - Auto-create security case with full request context
  - Log session ID for potential blocking
- **Context:** User session history, IP geolocation, prompt content (redacted PII)

### Rule 3: Cost-Per-Conversion Anomaly (Business Impact)

**Innovation:** Ties LLM costs directly to business outcomes

- **Signal:** Composite metric `llm.cost_per_conversion = total_token_cost / successful_checkouts`
- **Implementation:** 
  - Track token costs per chatbot session
  - Correlate with checkout events via session ID
  - Calculate rolling cost-per-conversion
- **Trigger:** Cost-per-conversion exceeds 7-day moving average by 100%
- **Severity:** Medium (financial impact)
- **Action:** Create case with:
  - Breakdown by service (chatbot vs PEAU agent)
  - Most expensive conversation patterns
  - AI-generated optimization suggestions from Observability Insights Service
- **Runbook:** Review prompt lengths, check for conversation loops, evaluate model tier appropriateness

### Rule 4: Response Quality Degradation (User Experience)

**Innovation:** Proactive detection of LLM quality issues before user complaints

- **Signal:** Custom metric `llm.response.quality_score` (0-1)
- **Implementation:**
  - Measure response coherence (via lightweight classifier)
  - Track response length anomalies (too short = unhelpful, too long = rambling)
  - Monitor product ID extraction success rate
  - User engagement signals (did user click recommended product?)
- **Trigger:** Quality score drops below 0.6 for > 5 minutes OR sudden 20% drop
- **Severity:** High
- **Action:** Create incident with:
  - Sample degraded responses
  - Correlation with model latency (is the model being rate-limited?)
  - Recent deployment changes
- **Runbook:** Check Vertex AI quotas, verify model endpoint health, review context window usage

### Rule 5: Predictive Capacity Alert (AI-Powered)

**Innovation:** Uses Observability Insights Service to predict failures before they happen

- **Signal:** Composite from `llm.request.rate`, `llm.latency.p99`, `llm.error.rate`
- **Implementation:**
  - Observability Insights Service analyzes 24h traffic patterns
  - Gemini predicts if current trajectory will hit rate limits or cause degradation
  - Generates confidence-scored predictions
- **Trigger:** Prediction confidence > 80% for failure within next 2 hours
- **Severity:** Warning → escalates to High if not acknowledged
- **Action:** 
  - Proactive alert with predicted failure time
  - Auto-generated scaling recommendations
  - Historical pattern comparison
- **Context:** Traffic forecast, current resource utilization, similar past incidents

---

## Custom Metrics to Emit

```python
# Metrics emitted by instrumented services
CUSTOM_METRICS = {
    # LLM Performance
    "llm.request.duration": "histogram",      # Response time
    "llm.tokens.input": "count",              # Input tokens per request
    "llm.tokens.output": "count",             # Output tokens per request
    "llm.tokens.total_cost_usd": "gauge",     # Calculated cost
    
    # Quality Signals
    "llm.response.quality_score": "gauge",    # 0-1 quality assessment
    "llm.recommendation.invalid_product_rate": "gauge",
    "llm.response.length_chars": "histogram",
    
    # Security
    "llm.security.injection_attempt_score": "gauge",
    "llm.security.pii_detected": "count",
    
    # Business
    "llm.session.converted": "count",         # Sessions that led to checkout
    "llm.cost_per_conversion": "gauge",
    
    # Predictions (from Insights Service)
    "llm.prediction.error_probability": "gauge",
    "llm.prediction.cost_forecast_24h": "gauge"
}
```

---

## Phase 4: Datadog Dashboard

### Dashboard Sections

1. **Application Health Overview**

   - Service map with LLM services highlighted
   - Overall latency, errors, throughput (RED metrics)
   - SLO status widgets

2. **LLM Observability Panel**

   - Token usage by service (input vs output)
   - Cost tracking over time
   - Model performance comparison
   - Prompt/response latency distribution

3. **AI Insights Panel**

   - Error predictions from Observability Insights Service
   - Cost optimization recommendations
   - Health summary (Gemini-generated)

4. **Detection Rules Status**

   - Monitor status for all 3 rules
   - Recent incidents/cases timeline

---

## Phase 5: Incident/Case Management

- Configure Datadog Incident Management integration
- Create runbooks for each detection rule
- Set up notification channels (Slack/email simulation)
- Include contextual data: affected service, error samples, suggested actions

---

## File Changes Summary

| File | Action |

|------|--------|

| `src/chatbotservice/chatbot_server.py` | Add ddtrace instrumentation |

| `src/chatbotservice/requirements.txt` | Add `ddtrace` |

| `src/chatbotservice/Dockerfile` | Add DD env vars |

| `src/peau_agent/peau_agent.py` | Add ddtrace instrumentation |

| `src/peau_agent/requirements.txt` | Add `ddtrace` |

| `src/shoppingassistantservice/shoppingassistantservice.py` | Add ddtrace |

| `src/shoppingassistantservice/requirements.txt` | Add `ddtrace` |

| `src/observability_insights_service/` | **NEW** - Full service |

| `kubernetes-manifests/observability-insights-service.yaml` | **NEW** |

| `kubernetes-manifests/datadog-agent.yaml` | **NEW** |

---

## Local Testing Workflow

1. Start Datadog Agent container with API key
2. Run instrumented services with `ddtrace-run`
3. Generate load to produce telemetry
4. Verify data in Datadog UI
5. Test detection rules trigger correctly

## GKE Deployment

1. Deploy Datadog Agent as DaemonSet
2. Configure admission controller for auto-instrumentation
3. Apply Kubernetes manifests with DD env vars
4. Import dashboard JSON to Datadog
5. Validate end-to-end flow