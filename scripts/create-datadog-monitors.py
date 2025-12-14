#!/usr/bin/env python3
"""
Datadog Detection Rules Creator

This script creates the 5 LLM detection rules as Datadog monitors using the API.
The detection rules are designed for the v-commerce LLM application.

Detection Rules:
1. Hallucination Detection - Invalid product recommendations
2. Prompt Injection Detection - Security-focused adversarial input detection
3. Cost-Per-Conversion Anomaly - Business impact correlation
4. Response Quality Degradation - User experience monitoring
5. Predictive Capacity Alert - AI-powered failure prediction

Usage:
    source .env.datadog
    python3 scripts/create-datadog-monitors.py

Requirements:
    pip install requests
    
Environment Variables:
    DD_API_KEY - Datadog API key
    DD_APP_KEY - Datadog Application key
    DD_SITE - Datadog site (default: datadoghq.com)
"""

import os
import json
import requests
import sys
from typing import Dict, Any, List

# Datadog API configuration
DD_API_KEY = os.getenv("DD_API_KEY", "")
DD_APP_KEY = os.getenv("DD_APP_KEY", "")
DD_SITE = os.getenv("DD_SITE", "us5.datadoghq.com")

API_BASE_URL = f"https://{DD_SITE}/api/v1"


def get_headers() -> Dict[str, str]:
    """Return headers for Datadog API requests."""
    return {
        "DD-API-KEY": DD_API_KEY,
        "DD-APPLICATION-KEY": DD_APP_KEY,
        "Content-Type": "application/json"
    }


def validate_credentials() -> bool:
    """Validate Datadog API credentials."""
    if not DD_API_KEY or not DD_APP_KEY:
        print("❌ Error: DD_API_KEY and DD_APP_KEY environment variables are required.")
        print("   Please source your .env.datadog file first:")
        print("   $ source .env.datadog")
        return False
    
    # Test API connectivity
    url = f"{API_BASE_URL}/validate"
    try:
        response = requests.get(url, headers={"DD-API-KEY": DD_API_KEY})
        if response.status_code == 200:
            print(f"✅ API Key validated for site: {DD_SITE}")
        else:
            print(f"❌ API validation failed: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False
    
    # Note: We skip checking application key scopes via API as it requires additional permissions
    # We'll just try to create monitors and handle any permission errors there
    print(f"✅ Application Key provided (will verify on first API call)")
    return True


def create_monitor(monitor_config: Dict[str, Any]) -> Dict[str, Any]:
    """Create a single monitor in Datadog."""
    url = f"{API_BASE_URL}/monitor"
    
    # Build the monitor payload
    payload = {
        "name": monitor_config["name"],
        "type": monitor_config["type"],
        "query": monitor_config["query"],
        "message": monitor_config["message"],
        "tags": monitor_config.get("tags", []),
        "priority": monitor_config.get("priority", 3),
        "options": monitor_config.get("options", {})
    }
    
    response = requests.post(url, headers=get_headers(), json=payload)
    return response.json()


def get_detection_rules() -> List[Dict[str, Any]]:
    """Return the 5 LLM detection rules."""
    return [
        # Rule 1: Hallucination Detection
        {
            "name": "[V-Commerce] LLM Hallucination Detection - Invalid Product Recommendations",
            "type": "metric alert",
            "query": "avg(last_10m):avg:llm.recommendation.invalid_product_rate{env:hackathon,service:v-commerce} > 0.02",
            "message": """## 🚨 LLM Hallucination Detected

**Service:** {{service.name}}
**Environment:** {{env}}

### What's happening?
The LLM is recommending products that don't exist in our catalog. The invalid product rate has exceeded 2% over the last 10 minutes.

**Current Rate:** {{value}}
**Threshold:** 2% (0.02)

### Impact
- Direct impact on user trust
- Potential revenue loss from bad recommendations
- Customer confusion and frustration

### Investigation Steps
1. Check RAG corpus freshness - Is the product catalog synced?
2. Review recent prompt/system message changes
3. Verify ProductCatalogService is returning complete data
4. Check for model drift or context window issues

### Runbook
- Verify product catalog sync timestamp
- Review LLM response samples in LLM Observability
- Check for recent deployments
- Consider prompt engineering fixes if pattern persists

@slack-llm-alerts""",
            "tags": [
                "env:hackathon",
                "service:v-commerce",
                "team:llm",
                "detection_rule:hallucination",
                "severity:high",
                "category:quality"
            ],
            "options": {
                "thresholds": {
                    "critical": 0.02,
                    "warning": 0.01
                },
                "notify_no_data": False,
                "renotify_interval": 30,
                "include_tags": True,
                "require_full_window": True,
                "new_host_delay": 300,
                "evaluation_delay": 60
            },
            "priority": 2
        },
        
        # Rule 2: Prompt Injection Detection
        {
            "name": "[V-Commerce] LLM Prompt Injection / Adversarial Input Detection",
            "type": "metric alert",
            "query": "max(last_5m):max:llm.security.injection_attempt_score{env:hackathon,service:v-commerce} > 0.7",
            "message": """## 🔴 SECURITY ALERT: Prompt Injection Attempt Detected

**Service:** {{service.name}}
**Environment:** {{env}}

### What's happening?
A potential prompt injection or adversarial input attempt has been detected. The injection attempt score has exceeded 0.7 (high confidence).

**Injection Score:** {{value}}
**Threshold:** 0.7

### Potential Attack Vectors Detected
- System prompt extraction attempts
- Jailbreak attempts
- SQL/code injection patterns in prompts
- Instruction override attempts

### Immediate Actions Required
1. ⚠️ Review the suspicious request in LLM Observability traces
2. Check session ID and user context for repeat offenders
3. Consider temporary rate limiting for the source IP/session
4. Preserve logs for security investigation

### Security Runbook
- Extract full prompt from LLM Observability span
- Check user session history for patterns
- Review IP geolocation and request headers
- If confirmed malicious: block session, notify security team

@slack-security-alerts @pagerduty-security""",
            "tags": [
                "env:hackathon",
                "service:v-commerce",
                "team:security",
                "detection_rule:injection",
                "severity:critical",
                "category:security"
            ],
            "options": {
                "thresholds": {
                    "critical": 0.7,
                    "warning": 0.5
                },
                "notify_no_data": False,
                "renotify_interval": 10,
                "include_tags": True,
                "require_full_window": False,
                "new_host_delay": 0,
                "evaluation_delay": 0
            },
            "priority": 1
        },
        
        # Rule 3: Cost-Per-Conversion Anomaly
        {
            "name": "[V-Commerce] LLM Cost-Per-Conversion Anomaly Detection",
            "type": "metric alert",
            "query": "avg(last_1h):avg:llm.cost_per_conversion{env:hackathon,service:v-commerce} > 1.0",
            "message": """## 💰 Cost-Per-Conversion Anomaly Detected

**Service:** {{service.name}}
**Environment:** {{env}}

### What's happening?
The cost-per-conversion has exceeded the expected threshold. This means we're spending more on LLM tokens per successful checkout than budgeted.

**Current Cost/Conversion:** ${{value}}
**Threshold:** $1.00 per conversion

### Business Impact
- Direct impact on profit margins
- Potential sign of inefficient LLM usage
- May indicate conversation loops or overly long prompts

### Cost Breakdown Investigation
1. Check token usage by service (chatbot vs PEAU agent vs shopping assistant)
2. Identify most expensive conversation patterns
3. Review prompt lengths and response sizes
4. Check for conversation loops (user repeating questions)

### Optimization Suggestions
- Review and optimize system prompts for conciseness
- Implement response caching for common queries
- Consider model tier appropriateness (Gemini Flash vs Pro)
- Evaluate context window trimming strategies

### AI-Generated Insights
Check the Observability Insights Service dashboard for automated cost optimization recommendations.

@slack-finops @slack-llm-alerts""",
            "tags": [
                "env:hackathon",
                "service:v-commerce",
                "team:finops",
                "detection_rule:cost_anomaly",
                "severity:medium",
                "category:business"
            ],
            "options": {
                "thresholds": {
                    "critical": 1.0,
                    "warning": 0.5
                },
                "notify_no_data": False,
                "renotify_interval": 60,
                "include_tags": True,
                "require_full_window": True,
                "new_host_delay": 300,
                "evaluation_delay": 300
            },
            "priority": 3
        },
        
        # Rule 4: Response Quality Degradation
        {
            "name": "[V-Commerce] LLM Response Quality Degradation Alert",
            "type": "metric alert",
            "query": "avg(last_5m):avg:llm.response.quality_score{env:hackathon,service:v-commerce} < 0.6",
            "message": """## ⚠️ LLM Response Quality Degradation Detected

**Service:** {{service.name}}
**Environment:** {{env}}

### What's happening?
The LLM response quality score has dropped below acceptable levels. This indicates the chatbot/assistant responses are becoming less helpful to users.

**Current Quality Score:** {{value}}
**Threshold:** 0.6 (minimum acceptable)

### Quality Signals Affected
- Response coherence and relevance
- Product ID extraction success rate
- Response length appropriateness
- User engagement with recommendations

### Potential Root Causes
1. Model being rate-limited by Vertex AI
2. Context window overflow (too much history)
3. RAG retrieval returning irrelevant documents
4. Recent prompt/system message changes
5. Model endpoint health issues

### Investigation Steps
1. Check Vertex AI quotas and rate limits
2. Review sample degraded responses in LLM Observability
3. Verify model endpoint latency (high latency = potential throttling)
4. Check recent deployments to LLM services
5. Review context window usage patterns

### Runbook
- Verify Vertex AI quotas
- Check model endpoint health in GCP Console
- Review recent prompt changes in git history
- Consider fallback to cached responses if critical

@slack-llm-alerts @pagerduty-oncall""",
            "tags": [
                "env:hackathon",
                "service:v-commerce",
                "team:llm",
                "detection_rule:quality",
                "severity:high",
                "category:quality"
            ],
            "options": {
                "thresholds": {
                    "critical": 0.6,
                    "warning": 0.7
                },
                "notify_no_data": False,
                "renotify_interval": 15,
                "include_tags": True,
                "require_full_window": True,
                "new_host_delay": 300,
                "evaluation_delay": 60
            },
            "priority": 2
        },
        
        # Rule 5: Predictive Capacity Alert
        {
            "name": "[V-Commerce] AI-Powered Predictive Capacity Alert",
            "type": "metric alert",
            "query": "avg(last_15m):avg:llm.prediction.error_probability{env:hackathon,service:v-commerce} > 0.8",
            "message": """## 🔮 Predictive Alert: Failure Predicted Within 2 Hours

**Service:** {{service.name}}
**Environment:** {{env}}

### What's happening?
The AI-powered Observability Insights Service has predicted a high probability of failure within the next 2 hours based on current traffic patterns and system behavior.

**Prediction Confidence:** {{value}}
**Threshold:** 80% (0.8) confidence

### Predicted Failure Scenarios
- Approaching Vertex AI rate limits based on traffic trajectory
- Latency degradation pattern similar to past incidents
- Error rate trending upward
- Resource utilization approaching critical levels

### Proactive Actions Recommended
1. **Pre-scale resources** if using autoscaling
2. **Enable request queuing** to smooth traffic spikes
3. **Warm up caches** for common queries
4. **Alert downstream services** of potential degradation
5. **Prepare rollback plan** if recent deployment

### AI-Generated Analysis
The Observability Insights Service analyzed:
- 24-hour traffic patterns
- Current resource utilization trajectory
- Historical incident patterns
- Model latency trends

### Runbook
- Review current vs projected traffic
- Check scaling policies and limits
- Verify backup/failover readiness
- Notify stakeholders of potential impact

@slack-llm-alerts @slack-sre""",
            "tags": [
                "env:hackathon",
                "service:v-commerce",
                "team:sre",
                "detection_rule:predictive",
                "severity:warning",
                "category:capacity"
            ],
            "options": {
                "thresholds": {
                    "critical": 0.8,
                    "warning": 0.6
                },
                "notify_no_data": False,
                "renotify_interval": 30,
                "timeout_h": 2,
                "include_tags": True,
                "require_full_window": True,
                "new_host_delay": 300,
                "evaluation_delay": 60
            },
            "priority": 2
        }
    ]


def main():
    """Main function to create all detection rules."""
    print("=" * 60)
    print("🐕 V-Commerce Datadog Detection Rules Creator")
    print("=" * 60)
    print()
    
    # Validate credentials
    if not validate_credentials():
        sys.exit(1)
    
    print()
    print("📋 Creating 5 LLM Detection Rules...")
    print("-" * 40)
    
    rules = get_detection_rules()
    created_monitors = []
    failed_monitors = []
    
    for i, rule in enumerate(rules, 1):
        print(f"\n[{i}/5] Creating: {rule['name'][:50]}...")
        
        try:
            result = create_monitor(rule)
            
            if "id" in result:
                print(f"     ✅ Created successfully (ID: {result['id']})")
                created_monitors.append({
                    "name": rule["name"],
                    "id": result["id"],
                    "type": rule["type"]
                })
            elif "errors" in result:
                error_msg = result['errors']
                print(f"     ❌ Failed: {error_msg}")
                if "Forbidden" in str(error_msg):
                    print(f"        💡 Your Application Key needs 'monitors_write' scope.")
                    print(f"        👉 Create a new key at: https://app.{DD_SITE}/personal-settings/application-keys")
                failed_monitors.append({
                    "name": rule["name"],
                    "error": error_msg
                })
            else:
                print(f"     ⚠️ Unexpected response: {result}")
                failed_monitors.append({
                    "name": rule["name"],
                    "error": str(result)
                })
                
        except Exception as e:
            print(f"     ❌ Error: {e}")
            failed_monitors.append({
                "name": rule["name"],
                "error": str(e)
            })
    
    # Summary
    print()
    print("=" * 60)
    print("📊 Summary")
    print("=" * 60)
    print(f"✅ Successfully created: {len(created_monitors)} monitors")
    print(f"❌ Failed: {len(failed_monitors)} monitors")
    
    if created_monitors:
        print("\n📌 Created Monitors:")
        for monitor in created_monitors:
            print(f"   - [{monitor['id']}] {monitor['name']}")
    
    if failed_monitors:
        print("\n⚠️ Failed Monitors:")
        for monitor in failed_monitors:
            print(f"   - {monitor['name']}: {monitor['error']}")
    
    print()
    print("🔗 View monitors at:")
    print(f"   https://app.{DD_SITE}/monitors/manage")
    print()
    
    # Save created monitors to file
    if created_monitors:
        output_file = "datadog-exports/created-monitors.json"
        with open(output_file, "w") as f:
            json.dump(created_monitors, f, indent=2)
        print(f"💾 Monitor IDs saved to: {output_file}")
    
    return len(failed_monitors) == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
