# V-Commerce Incident Management Setup

This document describes the incident management configuration for the v-commerce application using Datadog Incident Management.

## Overview

V-Commerce uses Datadog Incident Management to handle operational incidents across all services, with special focus on LLM-related issues. The system is designed to:

1. **Automatically create incidents** from high-severity alerts
2. **Route incidents** to the appropriate on-call teams
3. **Provide context** through integrated runbooks and dashboards
4. **Track resolution** with standardized workflows

---

## Incident Severity Levels

| Severity | Name     | Description                | Response Time | Examples                                 |
| -------- | -------- | -------------------------- | ------------- | ---------------------------------------- |
| SEV-1    | Critical | Revenue or security impact | 5 min         | Checkout down, prompt injection detected |
| SEV-2    | High     | Significant user impact    | 15 min        | LLM quality degradation, high error rate |
| SEV-3    | Medium   | Moderate impact            | 1 hour        | Cost anomalies, slow responses           |
| SEV-4    | Low      | Minor impact               | 4 hours       | Non-critical service degradation         |

---

## Automatic Incident Creation Rules

### Rule 1: Security Incidents (SEV-1)

**Trigger:** Prompt injection detection alert fires

```yaml
rule_name: '[V-Commerce] Critical LLM Security Incident'
trigger:
  monitors:
    - '[V-Commerce] LLM Prompt Injection / Adversarial Input Detection'
  condition: 'alert'
incident_settings:
  title: 'Security: Prompt Injection Detected'
  severity: 'SEV-1'
  commander: '@security-oncall'
  notifications:
    - slack-security-alerts
    - pagerduty-security
  fields:
    root_cause: 'Security threat detected'
    customer_impact: 'Potential data exposure risk'
    services_affected:
      ['chatbotservice', 'shoppingassistantservice', 'peau_agent']
```

### Rule 2: LLM Quality Incidents (SEV-2)

**Trigger:** Hallucination or quality degradation alerts fire

```yaml
rule_name: '[V-Commerce] LLM Quality Degradation Incident'
trigger:
  monitors:
    - '[V-Commerce] LLM Hallucination Detection'
    - '[V-Commerce] LLM Response Quality Degradation Alert'
  condition: 'alert'
incident_settings:
  title: 'LLM Quality: Response Degradation Detected'
  severity: 'SEV-2'
  commander: '@llm-oncall'
  notifications:
    - slack-llm-alerts
  fields:
    root_cause: 'LLM quality degradation'
    customer_impact: 'Poor user experience, potential conversion loss'
    services_affected: ['chatbotservice', 'shoppingassistantservice']
```

### Rule 3: Tier 1 Service Incidents (SEV-1)

**Trigger:** Any Tier 1 service SLO violation

```yaml
rule_name: '[V-Commerce] Tier 1 Service Incident'
trigger:
  monitors:
    - '*' # Any monitor with tag tier:1
  tags:
    - 'tier:1'
  condition: 'alert'
incident_settings:
  title: 'Critical: Tier 1 Service Degradation'
  severity: 'SEV-1'
  commander: '@platform-oncall'
  notifications:
    - pagerduty-oncall
    - slack-critical
  fields:
    root_cause: 'To be determined'
    customer_impact: 'Revenue-impacting service degradation'
```

### Rule 4: Predictive Capacity Incidents (SEV-2)

**Trigger:** AI-powered prediction of failure

```yaml
rule_name: '[V-Commerce] Predictive Capacity Incident'
trigger:
  monitors:
    - '[V-Commerce] AI-Powered Predictive Capacity Alert'
  condition: 'alert'
incident_settings:
  title: 'Predictive: Potential Failure in 2 Hours'
  severity: 'SEV-2'
  commander: '@sre-oncall'
  notifications:
    - slack-sre
  fields:
    root_cause: 'AI-predicted capacity issue'
    customer_impact: 'Potential future degradation'
    timeline: 'Predicted failure within 2 hours'
```

---

## On-Call Rotations

### Team Definitions

| Team         | Slack Channel    | PagerDuty       | Responsibilities                     |
| ------------ | ---------------- | --------------- | ------------------------------------ |
| LLM Platform | #llm-alerts      | llm-oncall      | LLM services, quality, hallucination |
| Security     | #security-alerts | security-oncall | Injection detection, data protection |
| Platform/SRE | #sre-alerts      | platform-oncall | Infrastructure, scaling, reliability |
| Commerce     | #commerce-alerts | commerce-oncall | Checkout, payment, cart              |

### Escalation Policies

**LLM Platform Escalation:**

```
1. Primary: LLM Platform Engineer (0-15 min)
2. Secondary: LLM Tech Lead (15-30 min)
3. Tertiary: Engineering Manager (30+ min)
```

**Security Escalation:**

```
1. Primary: Security Engineer (0-5 min)
2. Secondary: Security Lead (5-15 min)
3. Tertiary: CISO (15+ min, for confirmed breaches)
```

**Platform/SRE Escalation:**

```
1. Primary: SRE On-call (0-15 min)
2. Secondary: SRE Lead (15-30 min)
3. Tertiary: VP Engineering (30+ min, for SEV-1)
```

---

## Incident Workflow

### Phase 1: Detection & Triage (0-5 min)

1. **Alert fires** → Monitor triggers based on threshold
2. **Incident created** → Auto-created for high-severity alerts
3. **Commander assigned** → Based on incident rule configuration
4. **Team notified** → Via Slack and/or PagerDuty

### Phase 2: Investigation (5-30 min)

1. **Acknowledge incident** in Datadog
2. **Review linked runbook** for investigation steps
3. **Check related dashboards** and traces
4. **Communicate status** in incident timeline
5. **Update severity** if needed based on impact assessment

### Phase 3: Mitigation (varies)

1. **Implement fix** based on runbook guidance
2. **Document actions** in incident timeline
3. **Verify resolution** through metrics
4. **Notify stakeholders** of status

### Phase 4: Resolution & Post-Mortem

1. **Resolve incident** in Datadog
2. **Complete timeline** with all actions taken
3. **Schedule post-mortem** for SEV-1/SEV-2
4. **Create follow-up tasks** for improvements

---

## Datadog Configuration Setup

### Step 1: Create Notification Channels

Navigate to: **Integrations → Integrations**

**Slack Integration:**

```
1. Install Datadog Slack app
2. Configure channels:
   - #llm-alerts
   - #security-alerts
   - #sre-alerts
   - #commerce-alerts
   - #critical-incidents
```

**PagerDuty Integration:**

```
1. Go to Integrations → PagerDuty
2. Add integration for each service:
   - llm-oncall
   - security-oncall
   - platform-oncall
   - commerce-oncall
```

### Step 2: Configure Incident Rules

Navigate to: **Incidents → Settings → Rules**

Create rules using the configurations above. For each rule:

1. Set the trigger conditions (monitors, tags)
2. Configure incident settings (severity, commander)
3. Add notification targets
4. Link to runbook documentation

### Step 3: Create Incident Templates

Navigate to: **Incidents → Settings → Templates**

**LLM Incident Template:**

```yaml
name: 'LLM Service Incident'
fields:
  - name: 'Affected LLM Service'
    type: 'dropdown'
    options: ['chatbotservice', 'shoppingassistantservice', 'peau_agent', 'all']
  - name: 'Quality Score at Detection'
    type: 'number'
  - name: 'Token Usage Anomaly'
    type: 'boolean'
  - name: 'User Sessions Affected'
    type: 'number'
```

**Security Incident Template:**

```yaml
name: 'Security Incident'
fields:
  - name: 'Attack Vector'
    type: 'dropdown'
    options: ['prompt_injection', 'jailbreak', 'data_extraction', 'unknown']
  - name: 'Attack Successful'
    type: 'boolean'
  - name: 'Data Exposed'
    type: 'boolean'
  - name: 'Source IP/Session Blocked'
    type: 'boolean'
```

### Step 4: Link Runbooks

For each monitor, add runbook link in the message:

```
{{#is_alert}}
📕 **Runbook:** https://github.com/v-commerce/v-commerce/blob/main/docs/RUNBOOKS.md#<section>
{{/is_alert}}
```

---

## Dashboard Links for Incidents

When an incident is created, include links to relevant dashboards:

| Incident Type   | Dashboard Link                  |
| --------------- | ------------------------------- |
| LLM Quality     | `/dashboard/llm-observability`  |
| Security        | `/dashboard/security-overview`  |
| Tier 1 Services | `/dashboard/application-health` |
| Capacity        | `/dashboard/infrastructure`     |

---

## Post-Mortem Process

### Required for SEV-1 and SEV-2 incidents

**Timeline:** Schedule within 48 hours of resolution

**Attendees:**

- Incident Commander
- Team members involved in resolution
- Affected service owners
- Engineering Manager (SEV-1 only)

**Document Structure:**

```markdown
# Post-Mortem: [Incident Title]

## Summary

[Brief description of what happened]

## Timeline

[Chronological list of events]

## Root Cause

[Technical explanation of the root cause]

## Impact

- Duration: X minutes
- Users affected: Y
- Revenue impact: $Z (if applicable)

## What Went Well

- [List positives]

## What Could Be Improved

- [List improvements]

## Action Items

| Action     | Owner  | Due Date   |
| ---------- | ------ | ---------- |
| [Action 1] | @owner | YYYY-MM-DD |
```

---

## Metrics and Reporting

### Incident Metrics to Track

| Metric                          | Target           | Calculation                               |
| ------------------------------- | ---------------- | ----------------------------------------- |
| MTTD (Mean Time to Detect)      | < 5 min          | Time from issue start to alert            |
| MTTA (Mean Time to Acknowledge) | < 10 min         | Time from alert to acknowledgment         |
| MTTR (Mean Time to Resolve)     | < 1 hour (SEV-1) | Time from incident creation to resolution |
| Incident Count by Severity      | Trending down    | Weekly/monthly counts                     |
| Post-mortem Completion Rate     | 100% (SEV-1/2)   | Post-mortems completed vs required        |

### Weekly Incident Review

Every Monday, review:

1. Incidents from past week
2. Action item progress
3. SLO/error budget status
4. Emerging patterns

---

## API Commands for Incident Management

### Create Incident via API

```bash
curl -X POST "https://api.datadoghq.com/api/v2/incidents" \
  -H "DD-API-KEY: ${DD_API_KEY}" \
  -H "DD-APPLICATION-KEY: ${DD_APP_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "type": "incidents",
      "attributes": {
        "title": "Manual Incident: LLM Service Issue",
        "severity": "SEV-2",
        "state": "active",
        "customer_impacted": true,
        "fields": {
          "root_cause": {"value": "To be determined"},
          "services": {"value": ["chatbotservice"]}
        }
      }
    }
  }'
```

### List Active Incidents

```bash
curl -X GET "https://api.datadoghq.com/api/v2/incidents?filter[status]=active" \
  -H "DD-API-KEY: ${DD_API_KEY}" \
  -H "DD-APPLICATION-KEY: ${DD_APP_KEY}"
```

### Update Incident

```bash
curl -X PATCH "https://api.datadoghq.com/api/v2/incidents/{incident_id}" \
  -H "DD-API-KEY: ${DD_API_KEY}" \
  -H "DD-APPLICATION-KEY: ${DD_APP_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "type": "incidents",
      "attributes": {
        "state": "resolved"
      }
    }
  }'
```

---

## Quick Reference Card

### On Incident Creation

1. ✅ Acknowledge in Datadog
2. ✅ Join incident Slack channel
3. ✅ Open relevant runbook
4. ✅ Post initial assessment to timeline

### During Investigation

1. ✅ Document all findings in timeline
2. ✅ Tag related traces/logs
3. ✅ Update severity if needed
4. ✅ Communicate every 15 min (SEV-1) / 30 min (SEV-2)

### On Resolution

1. ✅ Verify metrics are normal
2. ✅ Update incident to resolved
3. ✅ Post summary to stakeholders
4. ✅ Schedule post-mortem (if required)

---

_Last Updated: December 2024_  
_Owner: SRE Team_
