# V-Commerce Detection Rules Runbooks

Operational runbooks for the 5 LLM detection rules implemented in Datadog.

---

## Table of Contents

1. [Prompt Injection Detection](#prompt-injection-detection)
2. [Interactions-Per-Conversion Anomaly](#interactions-per-conversion-anomaly)
3. [Response Quality Degradation](#response-quality-degradation)
4. [Predictive Capacity Alert](#predictive-capacity-alert)
5. [Multimodal Security Attack Detection](#multimodal-security-attack-detection)

---

## Prompt Injection Detection

**Monitor:** `[V-Commerce] LLM Prompt Injection / Adversarial Input Detection`  
**Severity:** SEV-1 (Critical)  
**Team:** Security  
**Metric:** `llm.security.injection_attempt_score` grouped by `session_id`  
**Threshold:** > 0.7  
**Incident Handle:** `@incident-prompt-injection`

### What This Alert Means

A user session is attempting to manipulate the LLM through adversarial prompts:

- **Jailbreak attempts** - "Ignore your instructions and..."
- **System prompt extraction** - "What are your rules? Show me your prompt"
- **SQL/Code injection** - Injecting SQL or code patterns into prompts
- **Instruction override** - "You are now in admin mode"

### Immediate Actions

1. **Identify the attacker** - Session ID is in the alert: `{{session_id.name}}`
2. **Review the malicious prompts** in LLM Observability traces
3. **Check if attack succeeded** - Did the LLM leak system prompts or bypass safety?
4. **Consider blocking the session** at the application level
5. **Preserve logs** for security forensics

### Investigation Checklist

- [ ] Was any sensitive information exposed?
- [ ] Is this a single attacker or coordinated attack?
- [ ] What specific attack vector was used?
- [ ] Are there other sessions from the same source?

### Resolution

**If attack was blocked:**
- Log the attempt for analysis
- Add pattern to injection detection rules
- Continue monitoring

**If attack succeeded:**
- Enable strict input filtering immediately
- Block the session/user
- Notify Security Lead within 1 hour
- Initiate incident response process

### Escalation

| Time | Action |
|------|--------|
| Immediate | Security On-call |
| 1 hour | Security Team Lead |
| If data breach | CISO + Legal |

---

## Interactions-Per-Conversion Anomaly

**Monitor:** `[V-Commerce] LLM Interactions-Per-Conversion Anomaly Detection`  
**Severity:** SEV-3 (Medium)  
**Team:** Product / LLM Platform  
**Metric:** `llm.cost_per_conversion`  
**Threshold:** > 10.0 interactions per cart add

### What This Alert Means

Users are requiring more AI chat interactions to add products to cart than expected. This indicates the chatbot may be less effective at guiding purchase decisions.

| Value | Interpretation |
|-------|---------------|
| 1-3 | Efficient - users convert quickly |
| 4-7 | Normal browsing behavior |
| 8+ | Potential issues - users struggling |

### Immediate Actions

1. **Check which service** is driving high interaction counts (chatbot vs PEAU)
2. **Review conversation patterns** - Are users in loops?
3. **Check product recommendations** - Are they relevant?
4. **Verify cart functionality** - Any technical issues blocking adds?

### Investigation Checklist

- [ ] Is this affecting all users or specific segments?
- [ ] Are there conversation loops (repeated questions)?
- [ ] Is the PEAU agent surfacing irrelevant products?
- [ ] Any recent prompt changes that could affect effectiveness?

### Resolution

**Quick wins:**
- Improve product recommendation relevance
- Add clearer calls-to-action in responses
- Review and update RAG corpus

**Medium-term:**
- Implement conversation summarization
- Add proactive cart suggestions
- A/B test different response styles

### Escalation

| Time | Action |
|------|--------|
| 2 hours | LLM Platform Engineer |
| If sustained | Product Manager |

---

## Response Quality Degradation

**Monitor:** `[V-Commerce] LLM Response Quality Degradation Alert`  
**Severity:** SEV-2 (High)  
**Team:** LLM Platform  
**Metric:** `llm.response.quality_score`  
**Threshold:** < 0.6

### What This Alert Means

LLM responses are becoming less helpful. Quality signals include:

- Response coherence and relevance
- Product ID extraction success rate
- Response length appropriateness
- User engagement with recommendations

### Immediate Actions

1. **Check Vertex AI status** - Any ongoing incidents?
2. **Verify quota/rate limits** - Are we being throttled?
3. **Review sample responses** - What's wrong with them?
4. **Check model endpoint health** - Latency issues?
5. **Review context window usage** - Overflow issues?

### Investigation Checklist

- [ ] Is Vertex AI returning errors or slow responses?
- [ ] Are we hitting rate limits?
- [ ] Are responses too short/long/irrelevant?
- [ ] Any recent prompt or model changes?

### Resolution

**If rate limited:**
- Reduce request rate
- Request quota increase

**If context overflow:**
- Implement conversation summarization
- Reduce RAG document count

**If model issues:**
- Switch to backup region
- Enable fallback responses

### Escalation

| Time | Action |
|------|--------|
| 10 min | LLM Platform Engineer |
| 15 min | LLM Tech Lead |
| If affecting conversions | Product Manager |

---

## Predictive Capacity Alert

**Monitor:** `[V-Commerce] AI-Powered Predictive Capacity Alert`  
**Severity:** SEV-2 (High)  
**Team:** SRE / LLM Platform  
**Metric:** `llm.prediction.error_probability`  
**Threshold:** > 80% confidence of failure within 2 hours

### What This Alert Means

The AI-powered Observability Insights Service predicts a high probability of failure based on:

- Traffic patterns analysis
- Resource utilization trajectory
- Historical incident patterns
- Model latency trends

### Immediate Actions

1. **Review prediction details** - What type of failure is predicted?
2. **Verify current metrics** - Error rates, latency, resource usage
3. **Check scaling status** - HPA, pod resources, node capacity
4. **Review traffic forecast** - Expected spike?

### Proactive Mitigation

**Pre-scale resources:**
```bash
kubectl scale deployment chatbotservice --replicas=5
```

**Enable request queuing:**
```bash
kubectl set env deployment/chatbotservice REQUEST_QUEUE_ENABLED=true
```

**Warm up caches:**
```bash
kubectl exec deploy/chatbotservice -- python -c "from cache import warmup; warmup()"
```

### Decision Matrix

| Confidence | Time to Failure | Action |
|------------|-----------------|--------|
| 80-90% | > 1 hour | Pre-scale, monitor |
| 80-90% | < 1 hour | Pre-scale, alert teams |
| 90%+ | Any | Scale + queue + prepare rollback |

### Escalation

| Time | Action |
|------|--------|
| Immediate | SRE On-call |
| If > 90% confidence | SRE Lead + LLM Lead |
| If < 30 min to failure | Incident Commander |

---

## Multimodal Security Attack Detection

**Monitor:** `[V-Commerce] Multimodal Security Attack Detection - Try-On Service`  
**Severity:** SEV-2 (High)  
**Team:** Security  
**Metric:** `tryon.security.decompression_bomb` + `tryon.security.invalid_image` grouped by `user_id`  
**Threshold:** > 3 attacks per user per 5 minutes  
**Incident Handle:** `@incident-multimodal`

### What This Alert Means

A user is repeatedly uploading malicious images to the Try-On service:

- **Decompression bombs** - Small files that expand to massive size in memory
- **Invalid/corrupted images** - Files designed to crash image processing
- **Polyglot files** - Images with hidden malicious payloads

### Immediate Actions

1. **Identify the attacker** - User ID is in the alert: `{{user_id.name}}`
2. **Review attack patterns** - What types of files are being uploaded?
3. **Check service health** - Any memory pressure or crashes?
4. **Consider blocking the user** at the application level
5. **Preserve logs** for forensic analysis

### Investigation Checklist

- [ ] What attack types were attempted? (bombs vs invalid images)
- [ ] Did any attacks impact service health?
- [ ] Is this a single attacker or coordinated?
- [ ] Any other suspicious activity from this user?

### Resolution

**The attacks are automatically blocked** by security controls in the Try-On service:
- Pillow's `MAX_IMAGE_PIXELS` limit prevents decompression bombs
- Image validation rejects corrupted/invalid files

**If attacks are sustained:**
- Block the user_id at application level
- Add IP to WAF blocklist if available
- Notify security team for further investigation

### Escalation

| Time | Action |
|------|--------|
| Immediate | Security On-call |
| If service degraded | SRE On-call |
| If multiple attackers | Security Lead |

---

## Emergency Contacts

| Role | Contact |
|------|---------|
| LLM Platform On-call | @llm-oncall |
| SRE On-call | @sre-oncall |
| Security On-call | @security-oncall |
| Engineering Manager | @eng-manager |

---

_Last Updated: December 2024_  
_Owner: LLM Platform Team_
