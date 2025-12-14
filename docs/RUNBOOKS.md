# V-Commerce Detection Rule Runbooks

This document contains detailed runbooks for each of the 5 LLM detection rules implemented in Datadog. These runbooks guide on-call engineers through incident investigation and resolution.

---

## Table of Contents

1. [Hallucination Detection Runbook](#1-hallucination-detection-runbook)
2. [Prompt Injection Detection Runbook](#2-prompt-injection-detection-runbook)
3. [Cost-Per-Conversion Anomaly Runbook](#3-cost-per-conversion-anomaly-runbook)
4. [Response Quality Degradation Runbook](#4-response-quality-degradation-runbook)
5. [Predictive Capacity Alert Runbook](#5-predictive-capacity-alert-runbook)

---

## 1. Hallucination Detection Runbook

**Alert Name:** `[V-Commerce] LLM Hallucination Detection - Invalid Product Recommendations`  
**Severity:** High  
**Team:** LLM Platform  
**Metric:** `llm.recommendation.invalid_product_rate`  
**Threshold:** > 2% over 10 minutes

### What This Alert Means

The LLM is recommending products that don't exist in our product catalog. This typically happens when:

- The RAG corpus is out of sync with ProductCatalogService
- The LLM is generating product names/IDs that don't exist
- Context window is truncated, losing product information

### Impact Assessment

| Impact Area | Severity | Description                                     |
| ----------- | -------- | ----------------------------------------------- |
| User Trust  | High     | Users clicking non-existent products see errors |
| Revenue     | High     | Failed product links = lost conversions         |
| Brand       | Medium   | Makes the AI assistant appear unreliable        |

### Investigation Steps

#### Step 1: Check LLM Observability Traces (2 min)

```
1. Go to: Datadog > LLM Observability > Traces
2. Filter: service:chatbotservice OR service:shoppingassistantservice
3. Filter: @llm.response.has_invalid_product:true
4. Review 5-10 sample traces to identify patterns
```

**Questions to answer:**

- What products are being hallucinated?
- Is there a pattern in the user prompts?
- Are specific product categories affected?

#### Step 2: Verify RAG Corpus Freshness (3 min)

```bash
# Check last product catalog sync timestamp
kubectl logs -l app=productcatalogservice --tail=100 | grep "catalog sync"

# Verify product count in RAG corpus
curl http://chatbotservice:8080/debug/rag_stats
```

**Expected:** Sync timestamp should be < 1 hour old

#### Step 3: Check ProductCatalogService Health (2 min)

```
1. Go to: Datadog > APM > Services > productcatalogservice
2. Check error rate and latency
3. Verify gRPC endpoints are responding
```

#### Step 4: Review Recent Deployments (2 min)

```bash
# Check recent deployments
kubectl rollout history deployment/chatbotservice
kubectl rollout history deployment/shoppingassistantservice

# Check recent prompt/system message changes
git log --oneline -10 -- src/chatbotservice/ src/shoppingassistantservice/
```

### Resolution Actions

#### If RAG Corpus is Stale

```bash
# Trigger manual RAG sync
kubectl exec -it deploy/chatbotservice -- python -c "from rag import sync_catalog; sync_catalog()"
```

#### If ProductCatalogService is Down

1. Check Redis cache availability
2. Restart productcatalogservice if needed
3. Enable static catalog fallback

#### If Prompt Engineering Issue

1. Review recent changes to system prompts
2. Consider rolling back to last known good version
3. Add explicit instructions to verify product existence

### Escalation Path

1. **First 15 min:** LLM Platform Engineer on-call
2. **After 15 min:** Escalate to LLM Tech Lead
3. **If revenue impact confirmed:** Page Commerce team lead

### Post-Incident

- [ ] Update RAG sync monitoring
- [ ] Add product validation before response
- [ ] Document root cause in incident timeline

---

## 2. Prompt Injection Detection Runbook

**Alert Name:** `[V-Commerce] LLM Prompt Injection / Adversarial Input Detection`  
**Severity:** Critical  
**Team:** Security  
**Metric:** `llm.security.injection_attempt_score`  
**Threshold:** > 0.7 (high confidence)

### What This Alert Means

A potential security attack has been detected where a user is attempting to:

- Extract the system prompt
- Jailbreak the LLM to bypass safety guardrails
- Inject malicious instructions
- Perform SQL/code injection through LLM

### Impact Assessment

| Impact Area | Severity | Description                                    |
| ----------- | -------- | ---------------------------------------------- |
| Security    | Critical | Potential data exposure or system compromise   |
| Reputation  | High     | Public disclosure of vulnerabilities           |
| Compliance  | High     | May trigger data breach reporting requirements |

### IMMEDIATE ACTIONS (First 5 Minutes)

#### Step 1: Preserve Evidence

```bash
# Export relevant logs immediately
kubectl logs -l app=chatbotservice --since=30m > /tmp/injection_incident_$(date +%s).log

# Capture the suspicious trace ID from the alert
# Note: DO NOT share trace ID publicly
```

#### Step 2: Identify Attack Source

```
1. Go to: Datadog > LLM Observability > Traces
2. Find trace with high injection_attempt_score
3. Extract:
   - Session ID
   - User ID (if authenticated)
   - IP Address
   - Full prompt text (for security review only)
```

#### Step 3: Check for Data Exfiltration

```
1. Review LLM responses for the suspicious session
2. Check if system prompt was revealed
3. Verify no customer data was exposed
4. Check for unusual API patterns from the same source
```

### Investigation Checklist

- [ ] Was the attack successful? (Did the LLM leak information?)
- [ ] Is this a single attacker or coordinated attack?
- [ ] What attack vector was used? (jailbreak, extraction, injection)
- [ ] Are there other sessions from the same IP/user?

### Response Actions

#### If Attack Appears Successful

1. **IMMEDIATELY** enable stricter input filtering:

   ```bash
   kubectl set env deployment/chatbotservice STRICT_INPUT_FILTER=true
   ```

2. Block suspicious session/IP:

   ```bash
   # Add to WAF blocklist
   gcloud compute security-policies rules create 1000 \
     --security-policy=v-commerce-waf \
     --src-ip-ranges="<ATTACKER_IP>" \
     --action=deny-403
   ```

3. Notify Security team immediately via PagerDuty

#### If Attack Was Blocked

1. Log the attempt for security analysis
2. Add pattern to injection detection rules
3. Continue monitoring for follow-up attempts

### Security Notification Requirements

If data was exposed:

1. Notify Security Lead within 1 hour
2. Initiate security incident response process
3. Prepare breach notification if customer data affected

### Escalation Path

1. **Immediate:** Security On-call (PagerDuty)
2. **Within 1 hour:** Security Team Lead
3. **If data breach confirmed:** CISO + Legal

### Post-Incident

- [ ] Add attack pattern to detection rules
- [ ] Update input sanitization
- [ ] Conduct security review of LLM prompts
- [ ] Document in security incident log

---

## 3. Cost-Per-Conversion Anomaly Runbook

**Alert Name:** `[V-Commerce] LLM Cost-Per-Conversion Anomaly Detection`  
**Severity:** Medium  
**Team:** FinOps / LLM Platform  
**Metric:** `llm.cost_per_conversion`  
**Threshold:** > $1.00 per conversion (or 100% above 7-day average)

### What This Alert Means

We're spending more on LLM API costs per successful checkout than expected. This could indicate:

- Conversation loops (users repeating questions)
- Excessively long prompts or responses
- Increased usage without corresponding conversions
- Inefficient model usage (using Pro when Flash would suffice)

### Impact Assessment

| Impact Area    | Severity | Description                     |
| -------------- | -------- | ------------------------------- |
| Profitability  | Medium   | Direct impact on margins        |
| Sustainability | Medium   | Unsustainable cost trajectory   |
| Budget         | High     | May exceed allocated LLM budget |

### Investigation Steps

#### Step 1: Identify Cost Breakdown by Service (5 min)

```
1. Go to: Datadog > Dashboard > V-Commerce LLM Observability
2. Check "Token Usage by Service" panel
3. Identify which service is driving costs:
   - chatbotservice
   - peau_agent
   - shoppingassistantservice
```

#### Step 2: Analyze Conversation Patterns (5 min)

```
1. Go to: LLM Observability > Traces
2. Sort by token_count (descending)
3. Review top 10 most expensive conversations
4. Look for:
   - Long conversation loops
   - Repeated similar questions
   - Unusually long system prompts
   - Large context windows
```

#### Step 3: Check Conversion Rate (3 min)

```
1. Go to: Datadog > Dashboard > Business Metrics
2. Compare:
   - Chatbot sessions vs. checkouts
   - Session-to-conversion rate trend
3. Is cost up, or conversions down?
```

#### Step 4: Review Model Usage (3 min)

```bash
# Check which models are being used
kubectl logs -l app=chatbotservice --tail=500 | grep "model=" | sort | uniq -c

# Expected distribution:
# - gemini-2.0-flash for most requests
# - gemini-1.5-pro only for complex tasks
```

### Cost Optimization Actions

#### Quick Wins (< 1 hour)

1. **Enable response caching:**

   ```bash
   kubectl set env deployment/chatbotservice ENABLE_RESPONSE_CACHE=true CACHE_TTL=3600
   ```

2. **Reduce max tokens:**
   ```bash
   kubectl set env deployment/chatbotservice MAX_OUTPUT_TOKENS=500
   ```

#### Medium-Term (1-7 days)

1. **Review and optimize system prompts:**

   - Audit prompt length
   - Remove redundant instructions
   - Use few-shot examples judiciously

2. **Implement conversation summarization:**

   - Summarize long conversations instead of including full history
   - Limit context window to last N turns

3. **Model tiering:**
   - Route simple queries to Flash models
   - Reserve Pro models for complex reasoning

#### Strategic (1-4 weeks)

1. Implement semantic caching
2. Build prompt compression pipeline
3. Evaluate fine-tuned smaller models

### Escalation Path

1. **First 2 hours:** LLM Platform Engineer
2. **If daily cost exceeds 150% budget:** FinOps Lead
3. **If weekly trend continues:** Engineering Manager

### Cost Monitoring Commands

```bash
# Get current day's LLM costs
curl -s "https://api.datadoghq.com/api/v1/query" \
  -H "DD-API-KEY: ${DD_API_KEY}" \
  -H "DD-APPLICATION-KEY: ${DD_APP_KEY}" \
  --data-urlencode "query=sum:llm.tokens.total_cost_usd{env:hackathon}.rollup(sum, 86400)"
```

---

## 4. Response Quality Degradation Runbook

**Alert Name:** `[V-Commerce] LLM Response Quality Degradation Alert`  
**Severity:** High  
**Team:** LLM Platform  
**Metric:** `llm.response.quality_score`  
**Threshold:** < 0.6 for 5+ minutes OR sudden 20% drop

### What This Alert Means

LLM responses are becoming less helpful to users. Quality signals include:

- Response coherence and relevance
- Product ID extraction success rate
- Response length appropriateness
- User engagement with recommendations

### Impact Assessment

| Impact Area     | Severity | Description                        |
| --------------- | -------- | ---------------------------------- |
| User Experience | High     | Frustrating, unhelpful responses   |
| Conversion      | High     | Poor recommendations = lower sales |
| Trust           | Medium   | Users may abandon the chatbot      |

### Investigation Steps

#### Step 1: Check Vertex AI Status (2 min)

```
1. Go to: https://status.cloud.google.com/
2. Check Vertex AI service status
3. Check for any ongoing incidents
```

#### Step 2: Verify Quota and Rate Limits (3 min)

```bash
# Check Vertex AI quota usage
gcloud ml quotas list --service=aiplatform.googleapis.com --region=us-central1

# Check rate limit errors in logs
kubectl logs -l app=chatbotservice --tail=500 | grep -i "rate limit\|quota\|429"
```

#### Step 3: Review LLM Response Samples (5 min)

```
1. Go to: Datadog > LLM Observability > Traces
2. Filter: llm.response.quality_score < 0.6
3. Review 10 sample responses:
   - Are responses too short/long?
   - Are they relevant to the question?
   - Do they contain product IDs?
   - Is the formatting correct?
```

#### Step 4: Check Model Endpoint Health (3 min)

```bash
# Test model endpoint directly
curl -X POST "https://us-central1-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/us-central1/publishers/google/models/gemini-2.0-flash:generateContent" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"Hello, test"}]}]}'
```

#### Step 5: Check Context Window Usage (3 min)

```
1. Go to: LLM Observability > Traces
2. Check token counts for recent requests
3. Look for:
   - Very high input token counts (context overflow)
   - Truncated prompts
   - Missing RAG context
```

### Resolution Actions

#### If Rate Limited

1. **Immediate:** Reduce request rate

   ```bash
   kubectl set env deployment/chatbotservice RATE_LIMIT_RPM=30
   ```

2. **Request quota increase** via GCP Console

#### If Context Overflow

1. Implement conversation summarization
2. Reduce RAG document count
3. Trim system prompt length

#### If Model Endpoint Issues

1. Switch to backup model/region

   ```bash
   kubectl set env deployment/chatbotservice MODEL_ENDPOINT=us-east1
   ```

2. Enable fallback to simpler responses

#### If Quality Classifier Issue

1. Review quality scoring logic
2. Check for classifier drift
3. Verify training data is still relevant

### Emergency Fallback

If quality cannot be restored quickly:

```bash
# Enable degraded mode with cached/template responses
kubectl set env deployment/chatbotservice DEGRADED_MODE=true
```

### Escalation Path

1. **First 10 min:** LLM Platform Engineer
2. **After 15 min:** LLM Tech Lead
3. **If affecting conversions:** Product Manager

---

## 5. Predictive Capacity Alert Runbook

**Alert Name:** `[V-Commerce] AI-Powered Predictive Capacity Alert`  
**Severity:** Warning → High  
**Team:** SRE / LLM Platform  
**Metric:** `llm.prediction.error_probability`  
**Threshold:** > 80% confidence of failure within 2 hours

### What This Alert Means

The AI-powered Observability Insights Service has analyzed:

- 24-hour traffic patterns
- Current resource utilization trajectory
- Historical incident patterns
- Model latency trends

And predicts a high probability of failure within the next 2 hours.

### Impact Assessment

| Impact Area     | Severity | Description                             |
| --------------- | -------- | --------------------------------------- |
| Availability    | High     | Predicted service degradation           |
| User Experience | High     | Potential for widespread failures       |
| Revenue         | Medium   | Proactive mitigation can prevent losses |

### Investigation Steps

#### Step 1: Review Prediction Details (3 min)

```
1. Go to: Datadog > Dashboard > AI Insights Panel
2. Review:
   - Predicted failure type
   - Confidence score
   - Contributing factors
   - Historical similar incidents
```

#### Step 2: Verify Current Metrics (5 min)

```
1. Go to: Datadog > APM > Services
2. Check for each LLM service:
   - Request rate trend
   - Error rate trend
   - Latency P99 trend
   - Resource utilization
```

#### Step 3: Check Scaling Status (3 min)

```bash
# Check current HPA status
kubectl get hpa

# Check pod resource usage
kubectl top pods -l team=llm

# Check node capacity
kubectl describe nodes | grep -A 5 "Allocated resources"
```

#### Step 4: Review Traffic Forecast (2 min)

```
1. Compare current traffic to:
   - Same time last week
   - Same time yesterday
2. Is there an expected traffic spike? (marketing campaign, sale, etc.)
```

### Proactive Mitigation Actions

#### Pre-Scale Resources

```bash
# Increase replica count proactively
kubectl scale deployment chatbotservice --replicas=5
kubectl scale deployment shoppingassistantservice --replicas=3

# Or update HPA min replicas
kubectl patch hpa chatbotservice -p '{"spec":{"minReplicas":5}}'
```

#### Enable Request Queuing

```bash
kubectl set env deployment/chatbotservice \
  REQUEST_QUEUE_ENABLED=true \
  REQUEST_QUEUE_MAX_SIZE=100 \
  REQUEST_TIMEOUT_MS=30000
```

#### Warm Up Caches

```bash
# Trigger cache warm-up for common queries
kubectl exec deploy/chatbotservice -- python -c "from cache import warmup; warmup()"
```

#### Alert Downstream Services

Notify teams that may be affected:

- Frontend team (for graceful degradation)
- Commerce team (for checkout flow monitoring)
- Customer support (for increased inquiries)

#### Prepare Rollback

If recent deployment is a factor:

```bash
# Check recent deployments
kubectl rollout history deployment/chatbotservice

# Prepare rollback command (don't execute yet)
# kubectl rollout undo deployment/chatbotservice
```

### Decision Matrix

| Confidence | Time to Failure | Action                                   |
| ---------- | --------------- | ---------------------------------------- |
| 80-90%     | > 1 hour        | Pre-scale, monitor closely               |
| 80-90%     | < 1 hour        | Pre-scale, alert teams                   |
| 90%+       | > 1 hour        | Pre-scale, prepare rollback              |
| 90%+       | < 1 hour        | Scale + queue + alert + prepare rollback |

### Escalation Path

1. **Immediate:** SRE On-call
2. **If confidence > 90%:** SRE Lead + LLM Platform Lead
3. **If < 30 min to predicted failure:** Incident Commander

### Post-Event

Whether the prediction was accurate or not:

- [ ] Document prediction accuracy
- [ ] Tune prediction model if needed
- [ ] Update scaling policies
- [ ] Add to capacity planning review

---

## Appendix: Common Commands

### LLM Service Logs

```bash
# Chatbot logs
kubectl logs -l app=chatbotservice --tail=100 -f

# Shopping Assistant logs
kubectl logs -l app=shoppingassistantservice --tail=100 -f

# PEAU Agent logs
kubectl logs -l app=peau-agent --tail=100 -f
```

### Datadog API Queries

```bash
# Get current alert status
curl -s "https://api.datadoghq.com/api/v1/monitor" \
  -H "DD-API-KEY: ${DD_API_KEY}" \
  -H "DD-APPLICATION-KEY: ${DD_APP_KEY}" | jq '.[] | select(.name | contains("V-Commerce"))'
```

### Emergency Contacts

| Role                 | Contact          |
| -------------------- | ---------------- |
| LLM Platform On-call | @llm-oncall      |
| SRE On-call          | @sre-oncall      |
| Security On-call     | @security-oncall |
| Engineering Manager  | @eng-manager     |

---

_Last Updated: December 2024_  
_Owner: LLM Platform Team_
