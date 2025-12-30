#!/usr/bin/env python3
"""
Datadog Detection Rules Creator

This script creates the LLM detection rules as Datadog monitors using the API.
The detection rules are designed for the v-commerce LLM application.

Detection Rules:
1. Prompt Injection Detection - Security-focused adversarial input detection
2. Interactions-Per-Conversion Anomaly - AI chat efficiency (how many chats to convert)
3. Response Quality Degradation - User experience monitoring
4. Predictive Capacity Alert - AI-powered failure prediction
5. Multimodal Security Attack Detection - Try-On service image attack detection

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
    """Return the 6 LLM detection rules."""
    return [
        
#         # Rule 2: Prompt Injection Detection
#         {
#             "name": "[V-Commerce] LLM Prompt Injection / Adversarial Input Detection",
#             "type": "metric alert",
#             "query": "max(last_5m):max:llm.security.injection_attempt_score{env:hackathon,service:v-commerce} > 0.7",
#             "message": """## 🔴 SECURITY ALERT: Prompt Injection Attempt Detected

# **Service:** {{service.name}}
# **Environment:** {{env}}

# ### What's happening?
# A potential prompt injection or adversarial input attempt has been detected. The injection attempt score has exceeded 0.7 (high confidence).

# **Injection Score:** {{value}}
# **Threshold:** 0.7

# ### Potential Attack Vectors Detected
# - System prompt extraction attempts
# - Jailbreak attempts
# - SQL/code injection patterns in prompts
# - Instruction override attempts

# ### Immediate Actions Required
# 1. ⚠️ Review the suspicious request in LLM Observability traces
# 2. Check session ID and user context for repeat offenders
# 3. Consider temporary rate limiting for the source IP/session
# 4. Preserve logs for security investigation

# ### Security Runbook
# - Extract full prompt from LLM Observability span
# - Check user session history for patterns
# - Review IP geolocation and request headers
# - If confirmed malicious: block session, notify security team

# @slack-security-alerts @pagerduty-security""",
#             "tags": [
#                 "env:hackathon",
#                 "service:v-commerce",
#                 "team:security",
#                 "detection_rule:injection",
#                 "severity:critical",
#                 "category:security"
#             ],
#             "options": {
#                 "thresholds": {
#                     "critical": 0.7,
#                     "warning": 0.5
#                 },
#                 "notify_no_data": False,
#                 "renotify_interval": 10,
#                 "include_tags": True,
#                 "require_full_window": False,
#                 "new_host_delay": 0,
#                 "evaluation_delay": 0
#             },
#             "priority": 1
#         },
        
        # Rule 3: Interactions-Per-Conversion Anomaly (formerly Cost-Per-Conversion)
        {
            "name": "[V-Commerce] LLM Interactions-Per-Conversion Anomaly Detection",
            "type": "metric alert",
            "query": "avg(last_1h):avg:llm.cost_per_conversion{env:hackathon,service:v-commerce} > 10.0",
            "message": """## 💬 High AI Interactions Per Conversion Detected

**Service:** {{service.name}}
**Environment:** {{env}}

### What's happening?
Users are requiring more AI chat interactions to convert (add items to cart) than expected. This indicates the chatbot may be less effective at guiding users to purchase decisions.

**Current Interactions/Conversion:** {{value}}
**Threshold:** 10.0 interactions per cart add

### What does this mean?
The `llm.cost_per_conversion` metric tracks **how many AI interactions it takes to get a user to add something to their cart**:

- **Low values (1-3):** Efficient - users convert quickly
- **Medium values (4-7):** Normal browsing behavior
- **High values (8+):** Potential issues - users need lots of help but aren't buying

### Business Impact
- Users may be confused or not finding what they want
- Chatbot responses may not be actionable enough
- Potential sign of poor product recommendations
- Wasted LLM resources on non-converting sessions

### Investigation Steps
1. Check quality of product recommendations (are they relevant?)
2. Review conversation patterns for stuck users
3. Check if PEAU agent suggestions are effective
4. Look for technical issues blocking cart adds
5. Compare user behavior by session to identify problem patterns

### Optimization Suggestions
- Improve product recommendation relevance
- Add clearer calls-to-action in responses
- Consider proactive cart suggestions earlier in conversations
- Review and update the RAG corpus for better product matching

### Related Metrics
- `llm.interaction_count` - Total interactions per session
- `llm.conversion_count` - Products added to cart
- `llm.source:chatbot` vs `llm.source:peau` - Interaction breakdown

@slack-product @slack-llm-alerts""",
            "tags": [
                "env:hackathon",
                "service:v-commerce",
                "team:product",
                "detection_rule:conversion_efficiency",
                "severity:medium",
                "category:business"
            ],
            "options": {
                "thresholds": {
                    "critical": 10.0,
                    "warning": 7.0
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
        
#         # Rule 4: Response Quality Degradation
#         {
#             "name": "[V-Commerce] LLM Response Quality Degradation Alert",
#             "type": "metric alert",
#             "query": "avg(last_5m):avg:llm.response.quality_score{env:hackathon,service:v-commerce} < 0.6",
#             "message": """## ⚠️ LLM Response Quality Degradation Detected

# **Service:** {{service.name}}
# **Environment:** {{env}}

# ### What's happening?
# The LLM response quality score has dropped below acceptable levels. This indicates the chatbot/assistant responses are becoming less helpful to users.

# **Current Quality Score:** {{value}}
# **Threshold:** 0.6 (minimum acceptable)

# ### Quality Signals Affected
# - Response coherence and relevance
# - Product ID extraction success rate
# - Response length appropriateness
# - User engagement with recommendations

# ### Potential Root Causes
# 1. Model being rate-limited by Vertex AI
# 2. Context window overflow (too much history)
# 3. RAG retrieval returning irrelevant documents
# 4. Recent prompt/system message changes
# 5. Model endpoint health issues

# ### Investigation Steps
# 1. Check Vertex AI quotas and rate limits
# 2. Review sample degraded responses in LLM Observability
# 3. Verify model endpoint latency (high latency = potential throttling)
# 4. Check recent deployments to LLM services
# 5. Review context window usage patterns

# ### Runbook
# - Verify Vertex AI quotas
# - Check model endpoint health in GCP Console
# - Review recent prompt changes in git history
# - Consider fallback to cached responses if critical

# @slack-llm-alerts @pagerduty-oncall""",
#             "tags": [
#                 "env:hackathon",
#                 "service:v-commerce",
#                 "team:llm",
#                 "detection_rule:quality",
#                 "severity:high",
#                 "category:quality"
#             ],
#             "options": {
#                 "thresholds": {
#                     "critical": 0.6,
#                     "warning": 0.7
#                 },
#                 "notify_no_data": False,
#                 "renotify_interval": 15,
#                 "include_tags": True,
#                 "require_full_window": True,
#                 "new_host_delay": 300,
#                 "evaluation_delay": 60
#             },
#             "priority": 2
#         },
        
#         # Rule 5: Predictive Capacity Alert
#         {
#             "name": "[V-Commerce] AI-Powered Predictive Capacity Alert",
#             "type": "metric alert",
#             "query": "avg(last_15m):avg:llm.prediction.error_probability{env:hackathon,service:v-commerce} > 0.8",
#             "message": """## 🔮 Predictive Alert: Failure Predicted Within 2 Hours

# **Service:** {{service.name}}
# **Environment:** {{env.name}}

# ### What's happening?
# The AI-powered Observability Insights Service has predicted a high probability of failure within the next 2 hours based on current traffic patterns and system behavior.

# **Prediction Confidence:** {{value}}
# **Threshold:** 80% (0.8) confidence

# ---

# ## 🤖 AI-Generated Analysis

# ### Root Cause
# {{root_cause.name}}

# ### Affected Services
# {{affected_services.name}}

# ### Recommended Actions
# {{actions_summary.name}}

# ### Time to Issue
# {{time_to_issue_hours.name}} hours

# ---

# ### Trigger Details
# - **Metric:** `llm.prediction.error_probability`
# - **Last 15min Average:** {{value}}
# - **All Tags:** {{tags}}

# ### Predicted Failure Scenarios
# - Approaching Vertex AI rate limits based on traffic trajectory
# - Latency degradation pattern similar to past incidents
# - Error rate trending upward
# - Resource utilization approaching critical levels

# ### 📊 View Full AI Analysis
# The Observability Insights Service generated this prediction. View the detailed AI analysis event:
# **[View AI Prediction Events in Datadog →](https://app.datadoghq.com/event/explorer?query=source%3Aobservability_insights%20prediction)**

# The event contains the complete Gemini-generated analysis with:
# - Detailed root cause explanation
# - Full list of affected services
# - Step-by-step recommended actions
# - Time-to-issue estimate

# ### Runbook
# 1. Review the AI-generated root cause analysis above
# 2. Check current vs projected traffic
# 3. Implement the recommended actions from the AI analysis
# 4. Verify scaling policies and limits
# 5. Notify stakeholders of potential impact

# @slack-llm-alerts @slack-sre""",
#             "tags": [
#                 "env:hackathon",
#                 "service:v-commerce",
#                 "team:sre",
#                 "detection_rule:predictive",
#                 "severity:warning",
#                 "category:capacity"
#             ],
#             "options": {
#                 "thresholds": {
#                     "critical": 0.8,
#                     "warning": 0.6
#                 },
#                 "notify_no_data": False,
#                 "renotify_interval": 30,
#                 "timeout_h": 2,
#                 "include_tags": True,
#                 "require_full_window": True,
#                 "new_host_delay": 300,
#                 "evaluation_delay": 60
#             },
#             "priority": 2
#         },
        
#         # Rule 6: Multimodal Security Attack Detection (Try-On Service)
#         {
#             "name": "[V-Commerce] Multimodal Security Attack Detection - Try-On Service",
#             "type": "metric alert",
#             "query": "sum(last_5m):sum:tryon.security.decompression_bomb{env:hackathon,service:tryonservice}.as_count() + sum:tryon.security.invalid_image{env:hackathon,service:tryonservice}.as_count() > 5",
#             "message": """## 🔴 SECURITY ALERT: Multimodal Attack Detected on Try-On Service

# **Service:** {{service.name}}
# **Environment:** {{env}}

# ### What's happening?
# The Try-On Service has detected multiple suspicious image uploads that may indicate an ongoing attack. This includes decompression bomb attempts and malformed/malicious image files.

# **Attack Count (5min):** {{value}}
# **Threshold:** 5 attacks per 5 minutes

# ### Attack Types Detected
# - **Decompression Bombs**: Malicious images designed to exhaust server memory when decompressed (e.g., a 1KB file that expands to gigabytes)
# - **Invalid/Malicious Images**: Corrupted files, polyglot files (images hiding malicious payloads), or files designed to exploit image processing vulnerabilities

# ### Immediate Actions Required
# 1. ⚠️ Check source IPs/sessions for repeat offenders
# 2. Review uploaded file patterns in APM traces
# 3. Consider temporary rate limiting for suspicious sources
# 4. Check server resource utilization (memory, CPU)
# 5. Preserve logs for security forensics

# ### Security Runbook
# - Extract request details from Datadog APM traces
# - Check for patterns: same user, same IP range, specific file signatures
# - If sustained attack: enable stricter file validation or temporary service protection mode
# - Notify security team if attack volume is high
# - Consider implementing CAPTCHA or additional verification for uploads

# ### Impact Assessment
# - Service availability may be degraded under attack
# - Memory exhaustion could crash pods
# - Potential for data exfiltration via polyglot files

# @slack-security-alerts @pagerduty-security""",
#             "tags": [
#                 "env:hackathon",
#                 "service:tryonservice",
#                 "team:security",
#                 "detection_rule:multimodal_security",
#                 "severity:critical",
#                 "category:security"
#             ],
#             "options": {
#                 "thresholds": {
#                     "critical": 5,
#                     "warning": 2
#                 },
#                 "notify_no_data": False,
#                 "renotify_interval": 10,
#                 "include_tags": True,
#                 "require_full_window": False,
#                 "new_host_delay": 0,
#                 "evaluation_delay": 0
#             },
#             "priority": 1
#         }
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
    print("📋 Creating 6 LLM Detection Rules...")
    print("-" * 40)
    
    rules = get_detection_rules()
    created_monitors = []
    failed_monitors = []
    
    for i, rule in enumerate(rules, 1):
        print(f"\n[{i}/6] Creating: {rule['name'][:50]}...")
        
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
