# Manual Detection Rules Setup in Datadog

If the API script fails with "Forbidden" errors, you can create the monitors manually in the Datadog UI.

## Quick Fix for API Script

The "Forbidden" error means your Application Key doesn't have `monitors_write` scope.

1. Go to: https://app.us5.datadoghq.com/personal-settings/application-keys
2. Click **"New Key"**
3. Name it: `v-commerce-monitors`
4. Select scopes:
   - `monitors_read`
   - `monitors_write`
5. Copy the new key and update `DD_APP_KEY`

---

## Manual Creation in Datadog UI

Go to: **https://app.us5.datadoghq.com/monitors/create/metric**

### Rule 1: Hallucination Detection

**Name:** `[V-Commerce] LLM Hallucination Detection - Invalid Product Recommendations`

**Type:** Metric Monitor

**Query:**

```
avg(last_10m):avg:llm.recommendation.invalid_product_rate{env:hackathon,service:v-commerce} > 0.02
```

**Thresholds:**

- Warning: 0.01
- Critical: 0.02

**Message:**

```
## 🚨 LLM Hallucination Detected

The LLM is recommending products that don't exist in our catalog.

**Current Rate:** {{value}}
**Threshold:** 2%

### Investigation Steps
1. Check RAG corpus freshness
2. Review recent prompt changes
3. Verify ProductCatalogService data

@slack-llm-alerts
```

**Tags:** `env:hackathon`, `service:v-commerce`, `detection_rule:hallucination`, `severity:high`

---

### Rule 2: Prompt Injection Detection

**Name:** `[V-Commerce] LLM Prompt Injection / Adversarial Input Detection`

**Type:** Metric Monitor

**Query:**

```
max(last_5m):max:llm.security.injection_attempt_score{env:hackathon,service:v-commerce} > 0.7
```

**Thresholds:**

- Warning: 0.5
- Critical: 0.7

**Message:**

```
## 🔴 SECURITY ALERT: Prompt Injection Attempt Detected

A potential prompt injection attempt has been detected.

**Injection Score:** {{value}}
**Threshold:** 0.7

### Immediate Actions
1. Review suspicious request in LLM Observability
2. Check session ID for repeat offenders
3. Consider rate limiting

@slack-security-alerts
```

**Tags:** `env:hackathon`, `service:v-commerce`, `detection_rule:injection`, `severity:critical`

---

### Rule 3: Cost-Per-Conversion Anomaly

**Name:** `[V-Commerce] LLM Cost-Per-Conversion Anomaly Detection`

**Type:** Metric Monitor

**Query:**

```
avg(last_1h):avg:llm.cost_per_conversion{env:hackathon,service:v-commerce} > 1.0
```

**Thresholds:**

- Warning: 0.5
- Critical: 1.0

**Message:**

```
## 💰 Cost-Per-Conversion Anomaly Detected

LLM spending per successful checkout has exceeded the threshold.

**Current Cost/Conversion:** ${{value}}
**Threshold:** $1.00

### Investigation
1. Check token usage by service
2. Identify expensive conversation patterns
3. Review prompt lengths

@slack-finops
```

**Tags:** `env:hackathon`, `service:v-commerce`, `detection_rule:cost_anomaly`, `severity:medium`

---

### Rule 4: Response Quality Degradation

**Name:** `[V-Commerce] LLM Response Quality Degradation Alert`

**Type:** Metric Monitor

**Query:**

```
avg(last_5m):avg:llm.response.quality_score{env:hackathon,service:v-commerce} < 0.6
```

**Thresholds:**

- Warning: 0.7
- Critical: 0.6

**Message:**

```
## ⚠️ LLM Response Quality Degradation Detected

Response quality has dropped below acceptable levels.

**Current Score:** {{value}}
**Threshold:** 0.6

### Root Causes
- Model rate limiting
- Context window overflow
- RAG retrieval issues

@slack-llm-alerts
```

**Tags:** `env:hackathon`, `service:v-commerce`, `detection_rule:quality`, `severity:high`

---

### Rule 5: Predictive Capacity Alert

**Name:** `[V-Commerce] AI-Powered Predictive Capacity Alert`

**Type:** Metric Monitor

**Query:**

```
avg(last_15m):avg:llm.prediction.error_probability{env:hackathon,service:v-commerce} > 0.8
```

**Thresholds:**

- Warning: 0.6
- Critical: 0.8

**Message:**

```
## 🔮 Predictive Alert: Failure Predicted Within 2 Hours

The AI Observability Insights Service predicts high probability of failure.

**Prediction Confidence:** {{value}}
**Threshold:** 80%

### Proactive Actions
1. Pre-scale resources
2. Enable request queuing
3. Warm up caches

@slack-sre
```

**Tags:** `env:hackathon`, `service:v-commerce`, `detection_rule:predictive`, `severity:warning`

---

## After Creating All Monitors

1. Go to **Monitors** > **Manage Monitors**
2. Filter by tag: `service:v-commerce`
3. Verify all 5 monitors appear
4. Take a screenshot for documentation

## Export Monitors (After Creation)

```bash
curl -X GET "https://api.us5.datadoghq.com/api/v1/monitor?tags=service:v-commerce" \
  -H "DD-API-KEY: ${DD_API_KEY}" \
  -H "DD-APPLICATION-KEY: ${DD_APP_KEY}" \
  | jq '.' > datadog-exports/monitors.json
```
