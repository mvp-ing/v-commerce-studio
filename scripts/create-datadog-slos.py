#!/usr/bin/env python3
"""
Datadog SLOs and Incident Management Creator

This script creates Service Level Objectives (SLOs) for the v-commerce application
using the Datadog API. It also sets up incident management workflows.

SLO Tiers:
- Tier 1 (Revenue Critical): Frontend, Checkout, Payment
- Tier 2 (User Experience): Chatbot LLM, Product Catalog, Cart
- Tier 3 (Supporting): Recommendations, Ads, Email

Usage:
    source .env.datadog
    python3 scripts/create-datadog-slos.py

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

API_BASE_URL_V1 = f"https://{DD_SITE}/api/v1"
API_BASE_URL_V2 = f"https://{DD_SITE}/api/v2"


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
    url = f"{API_BASE_URL_V1}/validate"
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
    
    print(f"✅ Application Key provided (will verify on first API call)")
    return True


def create_slo(slo_config: Dict[str, Any]) -> Dict[str, Any]:
    """Create a single SLO in Datadog."""
    url = f"{API_BASE_URL_V1}/slo"
    
    response = requests.post(url, headers=get_headers(), json=slo_config)
    return response.json()


def get_slos() -> List[Dict[str, Any]]:
    """Return all SLO configurations for v-commerce."""
    return [
        # ============================================
        # TIER 1: Revenue Critical Services (99.9%+)
        # ============================================
        
        # Frontend Availability SLO
        {
            "name": "[V-Commerce] Frontend Service Availability",
            "description": "Tier 1 SLO: Frontend service must be available 99.9% of the time. Error budget: 43.2 min/month. This is revenue-critical as it's the main customer entry point.",
            "type": "metric",
            "query": {
                "numerator": "sum:frontend.request.count{env:hackathon,service:frontend,!status:5*}.as_count()",
                "denominator": "sum:frontend.request.count{env:hackathon,service:frontend}.as_count()"
            },
            "thresholds": [
                {
                    "timeframe": "30d",
                    "target": 99.9,
                    "warning": 99.95
                },
                {
                    "timeframe": "7d",
                    "target": 99.9,
                    "warning": 99.95
                }
            ],
            "tags": [
                "env:hackathon",
                "service:frontend",
                "tier:1",
                "team:platform",
                "category:availability"
            ]
        },
        
        # Frontend Latency SLO
        {
            "name": "[V-Commerce] Frontend P95 Latency < 1s",
            "description": "Tier 1 SLO: 99.5% of frontend requests must complete within 1 second (P95). Poor latency directly impacts conversion rates and user experience.",
            "type": "metric",
            "query": {
                "numerator": "sum:frontend.request.duration.below_threshold{env:hackathon,service:frontend,threshold:1000}.as_count()",
                "denominator": "sum:frontend.request.count{env:hackathon,service:frontend}.as_count()"
            },
            "thresholds": [
                {
                    "timeframe": "30d",
                    "target": 99.5,
                    "warning": 99.7
                },
                {
                    "timeframe": "7d",
                    "target": 99.5,
                    "warning": 99.7
                }
            ],
            "tags": [
                "env:hackathon",
                "service:frontend",
                "tier:1",
                "team:platform",
                "category:latency"
            ]
        },
        
        # Checkout Success Rate SLO
        {
            "name": "[V-Commerce] Checkout Success Rate",
            "description": "Tier 1 SLO: Checkout service must succeed 99.5% of the time. Error budget: 3.6 hrs/month. Failed checkouts = lost revenue.",
            "type": "metric",
            "query": {
                "numerator": "sum:checkout.order.count{env:hackathon,service:checkoutservice,status:success}.as_count()",
                "denominator": "sum:checkout.order.count{env:hackathon,service:checkoutservice}.as_count()"
            },
            "thresholds": [
                {
                    "timeframe": "30d",
                    "target": 99.5,
                    "warning": 99.7
                },
                {
                    "timeframe": "7d",
                    "target": 99.5,
                    "warning": 99.7
                }
            ],
            "tags": [
                "env:hackathon",
                "service:checkoutservice",
                "tier:1",
                "team:commerce",
                "category:success_rate"
            ]
        },
        
        # Payment Transaction Success SLO
        {
            "name": "[V-Commerce] Payment Transaction Success Rate",
            "description": "Tier 1 SLO: Payment transactions must succeed 99.9% of the time. Error budget: 43.2 min/month. Payment failures are critical business blockers.",
            "type": "metric",
            "query": {
                "numerator": "sum:payment.transaction.count{env:hackathon,service:paymentservice,status:success}.as_count()",
                "denominator": "sum:payment.transaction.count{env:hackathon,service:paymentservice}.as_count()"
            },
            "thresholds": [
                {
                    "timeframe": "30d",
                    "target": 99.9,
                    "warning": 99.95
                },
                {
                    "timeframe": "7d",
                    "target": 99.9,
                    "warning": 99.95
                }
            ],
            "tags": [
                "env:hackathon",
                "service:paymentservice",
                "tier:1",
                "team:commerce",
                "category:success_rate"
            ]
        },
        
        # ============================================
        # TIER 2: User Experience Services (99-99.5%)
        # ============================================
        
        # Chatbot LLM Availability SLO
        {
            "name": "[V-Commerce] Chatbot LLM Availability",
            "description": "Tier 2 SLO: LLM-powered chatbot must be available 99.5% of the time. Error budget: 3.6 hrs/month. Chatbot enhances user experience but is not blocking for purchases.",
            "type": "metric",
            "query": {
                "numerator": "sum:llm.request.count{env:hackathon,service:chatbotservice,!status:error}.as_count()",
                "denominator": "sum:llm.request.count{env:hackathon,service:chatbotservice}.as_count()"
            },
            "thresholds": [
                {
                    "timeframe": "30d",
                    "target": 99.5,
                    "warning": 99.7
                },
                {
                    "timeframe": "7d",
                    "target": 99.5,
                    "warning": 99.7
                }
            ],
            "tags": [
                "env:hackathon",
                "service:chatbotservice",
                "tier:2",
                "team:llm",
                "category:availability"
            ]
        },
        
        # Chatbot LLM Response Time SLO
        {
            "name": "[V-Commerce] Chatbot LLM Response Time P95 < 5s",
            "description": "Tier 2 SLO: 99% of LLM chatbot responses must complete within 5 seconds. LLM latency tolerance is higher than standard APIs due to generation time.",
            "type": "metric",
            "query": {
                "numerator": "sum:llm.request.duration.below_threshold{env:hackathon,service:chatbotservice,threshold:5000}.as_count()",
                "denominator": "sum:llm.request.count{env:hackathon,service:chatbotservice}.as_count()"
            },
            "thresholds": [
                {
                    "timeframe": "30d",
                    "target": 99.0,
                    "warning": 99.3
                },
                {
                    "timeframe": "7d",
                    "target": 99.0,
                    "warning": 99.3
                }
            ],
            "tags": [
                "env:hackathon",
                "service:chatbotservice",
                "tier:2",
                "team:llm",
                "category:latency"
            ]
        },
        
        # Product Catalog Search Latency SLO
        {
            "name": "[V-Commerce] Product Catalog Search Latency P95 < 500ms",
            "description": "Tier 2 SLO: 99.5% of product searches must complete within 500ms. Fast search is critical for user experience and conversion.",
            "type": "metric",
            "query": {
                "numerator": "sum:catalog.search.duration.below_threshold{env:hackathon,service:productcatalogservice,threshold:500}.as_count()",
                "denominator": "sum:catalog.search.count{env:hackathon,service:productcatalogservice}.as_count()"
            },
            "thresholds": [
                {
                    "timeframe": "30d",
                    "target": 99.5,
                    "warning": 99.7
                },
                {
                    "timeframe": "7d",
                    "target": 99.5,
                    "warning": 99.7
                }
            ],
            "tags": [
                "env:hackathon",
                "service:productcatalogservice",
                "tier:2",
                "team:platform",
                "category:latency"
            ]
        },
        
        # Cart Operation Success SLO
        {
            "name": "[V-Commerce] Cart Operation Success Rate",
            "description": "Tier 2 SLO: Cart operations (add/remove/get) must succeed 99.9% of the time. Error budget: 43.2 min/month. Cart is essential for the purchase flow.",
            "type": "metric",
            "query": {
                "numerator": "sum:cart.operation.count{env:hackathon,service:cartservice,!status:error}.as_count()",
                "denominator": "sum:cart.operation.count{env:hackathon,service:cartservice}.as_count()"
            },
            "thresholds": [
                {
                    "timeframe": "30d",
                    "target": 99.9,
                    "warning": 99.95
                },
                {
                    "timeframe": "7d",
                    "target": 99.9,
                    "warning": 99.95
                }
            ],
            "tags": [
                "env:hackathon",
                "service:cartservice",
                "tier:2",
                "team:commerce",
                "category:success_rate"
            ]
        },
        
        # ============================================
        # TIER 3: Supporting Services (98-99%)
        # ============================================
        
        # Recommendations Availability SLO
        {
            "name": "[V-Commerce] Recommendation Service Availability",
            "description": "Tier 3 SLO: Recommendation service must be available 99% of the time. Error budget: 7.2 hrs/month. Recommendations enhance experience but are not critical.",
            "type": "metric",
            "query": {
                "numerator": "sum:recommendation.request.count{env:hackathon,service:recommendationservice,!status:error}.as_count()",
                "denominator": "sum:recommendation.request.count{env:hackathon,service:recommendationservice}.as_count()"
            },
            "thresholds": [
                {
                    "timeframe": "30d",
                    "target": 99.0,
                    "warning": 99.3
                },
                {
                    "timeframe": "7d",
                    "target": 99.0,
                    "warning": 99.3
                }
            ],
            "tags": [
                "env:hackathon",
                "service:recommendationservice",
                "tier:3",
                "team:platform",
                "category:availability"
            ]
        },
        
        # Ad Service Availability SLO
        {
            "name": "[V-Commerce] Ad Service Availability",
            "description": "Tier 3 SLO: Ad service must be available 99% of the time. Error budget: 7.2 hrs/month. Ads are supplementary and gracefully degrade.",
            "type": "metric",
            "query": {
                "numerator": "sum:ad.request.count{env:hackathon,service:adservice,!status:error}.as_count()",
                "denominator": "sum:ad.request.count{env:hackathon,service:adservice}.as_count()"
            },
            "thresholds": [
                {
                    "timeframe": "30d",
                    "target": 99.0,
                    "warning": 99.3
                },
                {
                    "timeframe": "7d",
                    "target": 99.0,
                    "warning": 99.3
                }
            ],
            "tags": [
                "env:hackathon",
                "service:adservice",
                "tier:3",
                "team:platform",
                "category:availability"
            ]
        },
        
        # Email Delivery Success SLO
        {
            "name": "[V-Commerce] Email Delivery Success Rate",
            "description": "Tier 3 SLO: Email service must successfully deliver 98% of emails. Error budget: 14.4 hrs/month. Emails are async and can tolerate retries.",
            "type": "metric",
            "query": {
                "numerator": "sum:email.sent.count{env:hackathon,service:emailservice,status:delivered}.as_count()",
                "denominator": "sum:email.sent.count{env:hackathon,service:emailservice}.as_count()"
            },
            "thresholds": [
                {
                    "timeframe": "30d",
                    "target": 98.0,
                    "warning": 98.5
                },
                {
                    "timeframe": "7d",
                    "target": 98.0,
                    "warning": 98.5
                }
            ],
            "tags": [
                "env:hackathon",
                "service:emailservice",
                "tier:3",
                "team:platform",
                "category:success_rate"
            ]
        },
        
        # ============================================
        # LLM-SPECIFIC SLOs
        # ============================================
        
        # LLM Quality Score SLO
        {
            "name": "[V-Commerce] LLM Response Quality Score",
            "description": "LLM SLO: Average response quality score must remain above 0.7 for 95% of the time. Low quality indicates hallucinations or irrelevant responses.",
            "type": "metric",
            "query": {
                "numerator": "sum:llm.response.quality_check.pass{env:hackathon}.as_count()",
                "denominator": "sum:llm.response.quality_check.total{env:hackathon}.as_count()"
            },
            "thresholds": [
                {
                    "timeframe": "30d",
                    "target": 95.0,
                    "warning": 97.0
                },
                {
                    "timeframe": "7d",
                    "target": 95.0,
                    "warning": 97.0
                }
            ],
            "tags": [
                "env:hackathon",
                "service:v-commerce-llm",
                "tier:2",
                "team:llm",
                "category:quality"
            ]
        },
        
        # LLM Cost Efficiency SLO
        {
            "name": "[V-Commerce] LLM Cost Per Conversion",
            "description": "LLM SLO: Cost per conversion should remain under $1.00 for 90% of the measurement period. Helps track ROI on LLM spending.",
            "type": "metric",
            "query": {
                "numerator": "sum:llm.cost_efficiency.within_budget{env:hackathon}.as_count()",
                "denominator": "sum:llm.cost_efficiency.total{env:hackathon}.as_count()"
            },
            "thresholds": [
                {
                    "timeframe": "30d",
                    "target": 90.0,
                    "warning": 93.0
                },
                {
                    "timeframe": "7d",
                    "target": 90.0,
                    "warning": 93.0
                }
            ],
            "tags": [
                "env:hackathon",
                "service:v-commerce-llm",
                "tier:2",
                "team:finops",
                "category:cost"
            ]
        }
    ]


def get_slo_burn_rate_alerts(slo_id: str, slo_name: str, tier: int) -> List[Dict[str, Any]]:
    """
    Generate burn rate alert configurations for an SLO.
    Returns monitor configurations for fast burn and slow burn alerts.
    """
    # Severity based on tier
    priority = {1: 1, 2: 2, 3: 3}.get(tier, 2)
    
    return [
        # Fast burn alert (1h window, 14.4x budget consumption rate)
        {
            "name": f"[V-Commerce] SLO Fast Burn Alert: {slo_name}",
            "type": "slo alert",
            "query": f"burn_rate(\"{slo_id}\").over(\"1h\").long_window(\"1h\").short_window(\"5m\") > 14.4",
            "message": f"""## 🔥 SLO Fast Burn Alert

**SLO:** {slo_name}
**Tier:** {tier}

### What's happening?
Error budget is being consumed at 14.4x the sustainable rate over the last hour. At this rate, the entire monthly error budget will be exhausted in ~2 days.

### Immediate Actions
1. Check for ongoing incidents or deployments
2. Review error logs for root cause
3. Consider rolling back recent changes
4. Escalate if cause is unknown

@pagerduty-oncall @slack-sre""",
            "tags": [
                "env:hackathon",
                f"tier:{tier}",
                "alert_type:slo_burn",
                "burn_rate:fast"
            ],
            "options": {
                "thresholds": {
                    "critical": 14.4
                }
            },
            "priority": priority
        },
        # Slow burn alert (6h window, 6x budget consumption rate)
        {
            "name": f"[V-Commerce] SLO Slow Burn Alert: {slo_name}",
            "type": "slo alert",
            "query": f"burn_rate(\"{slo_id}\").over(\"6h\").long_window(\"6h\").short_window(\"30m\") > 6",
            "message": f"""## ⚠️ SLO Slow Burn Alert

**SLO:** {slo_name}
**Tier:** {tier}

### What's happening?
Error budget is being consumed at 6x the sustainable rate over the last 6 hours. This is a slower degradation that needs investigation.

### Actions
1. Investigate gradual degradation causes
2. Check for capacity issues or gradual resource exhaustion
3. Review metrics trends for patterns
4. Plan remediation within the next few hours

@slack-sre""",
            "tags": [
                "env:hackathon",
                f"tier:{tier}",
                "alert_type:slo_burn",
                "burn_rate:slow"
            ],
            "options": {
                "thresholds": {
                    "critical": 6
                }
            },
            "priority": min(priority + 1, 3)
        }
    ]


def create_incident_rule(rule_config: Dict[str, Any]) -> Dict[str, Any]:
    """Create an incident workflow rule."""
    url = f"{API_BASE_URL_V2}/incidents/config/rules"
    response = requests.post(url, headers=get_headers(), json=rule_config)
    return response.json()


def get_incident_rules() -> List[Dict[str, Any]]:
    """Return incident management rules for automatic incident creation."""
    return [
        {
            "data": {
                "type": "incident_rule",
                "attributes": {
                    "name": "[V-Commerce] Critical LLM Security Incident",
                    "enabled": True,
                    "trigger": {
                        "monitor_ids": [],  # Will be populated with injection detection monitor
                        "severity": "SEV-1"
                    },
                    "cases": [
                        {
                            "condition": "monitor.tags contains 'detection_rule:injection'",
                            "notification_targets": ["slack-security-alerts"],
                            "incident_settings": {
                                "title": "Security: Prompt Injection Detected",
                                "severity": "SEV-1",
                                "commander": "@security-oncall",
                                "fields": {
                                    "root_cause": "Security threat detected",
                                    "customer_impact": "Potential data exposure risk"
                                }
                            }
                        }
                    ]
                }
            }
        },
        {
            "data": {
                "type": "incident_rule",
                "attributes": {
                    "name": "[V-Commerce] LLM Quality Degradation Incident",
                    "enabled": True,
                    "trigger": {
                        "monitor_ids": [],
                        "severity": "SEV-2"
                    },
                    "cases": [
                        {
                            "condition": "monitor.tags contains 'detection_rule:hallucination' OR monitor.tags contains 'detection_rule:quality'",
                            "notification_targets": ["slack-llm-alerts"],
                            "incident_settings": {
                                "title": "LLM Quality: Response Degradation Detected",
                                "severity": "SEV-2",
                                "commander": "@llm-oncall",
                                "fields": {
                                    "root_cause": "LLM quality degradation",
                                    "customer_impact": "Poor user experience, potential conversion loss"
                                }
                            }
                        }
                    ]
                }
            }
        },
        {
            "data": {
                "type": "incident_rule",
                "attributes": {
                    "name": "[V-Commerce] Tier 1 Service Incident",
                    "enabled": True,
                    "trigger": {
                        "monitor_ids": [],
                        "severity": "SEV-1"
                    },
                    "cases": [
                        {
                            "condition": "monitor.tags contains 'tier:1' AND monitor.status == 'Alert'",
                            "notification_targets": ["pagerduty-oncall", "slack-critical"],
                            "incident_settings": {
                                "title": "Critical: Tier 1 Service Degradation",
                                "severity": "SEV-1",
                                "commander": "@platform-oncall",
                                "fields": {
                                    "root_cause": "To be determined",
                                    "customer_impact": "Revenue-impacting service degradation"
                                }
                            }
                        }
                    ]
                }
            }
        }
    ]


def main():
    """Main function to create all SLOs and incident management."""
    print("=" * 60)
    print("🐕 V-Commerce Datadog SLOs & Incident Management Creator")
    print("=" * 60)
    print()
    
    # Validate credentials
    if not validate_credentials():
        sys.exit(1)
    
    print()
    
    # =====================
    # Create SLOs
    # =====================
    print("📊 Creating Service Level Objectives (SLOs)...")
    print("-" * 40)
    
    slos = get_slos()
    created_slos = []
    failed_slos = []
    
    for i, slo in enumerate(slos, 1):
        print(f"\n[{i}/{len(slos)}] Creating: {slo['name'][:50]}...")
        
        try:
            result = create_slo(slo)
            
            if "data" in result and len(result["data"]) > 0:
                slo_id = result["data"][0]["id"]
                print(f"     ✅ Created successfully (ID: {slo_id})")
                created_slos.append({
                    "name": slo["name"],
                    "id": slo_id,
                    "tags": slo.get("tags", [])
                })
            elif "errors" in result:
                error_msg = result['errors']
                print(f"     ❌ Failed: {error_msg}")
                failed_slos.append({
                    "name": slo["name"],
                    "error": error_msg
                })
            else:
                print(f"     ⚠️ Unexpected response: {result}")
                failed_slos.append({
                    "name": slo["name"],
                    "error": str(result)
                })
                
        except Exception as e:
            print(f"     ❌ Error: {e}")
            failed_slos.append({
                "name": slo["name"],
                "error": str(e)
            })
    
    # =====================
    # Summary
    # =====================
    print()
    print("=" * 60)
    print("📊 SLO Creation Summary")
    print("=" * 60)
    print(f"✅ Successfully created: {len(created_slos)} SLOs")
    print(f"❌ Failed: {len(failed_slos)} SLOs")
    
    if created_slos:
        print("\n📌 Created SLOs:")
        for slo in created_slos:
            tier_tag = next((t for t in slo.get("tags", []) if t.startswith("tier:")), "tier:unknown")
            print(f"   - [{tier_tag}] {slo['name']} (ID: {slo['id']})")
    
    if failed_slos:
        print("\n⚠️ Failed SLOs:")
        for slo in failed_slos:
            print(f"   - {slo['name']}: {slo['error']}")
    
    print()
    print("🔗 View SLOs at:")
    print(f"   https://app.{DD_SITE}/slo/manage")
    print()
    
    # =====================
    # Export to JSON
    # =====================
    output_dir = "datadog-exports"
    os.makedirs(output_dir, exist_ok=True)
    
    # Save created SLOs
    if created_slos:
        slo_output_file = f"{output_dir}/created-slos.json"
        with open(slo_output_file, "w") as f:
            json.dump(created_slos, f, indent=2)
        print(f"💾 SLO IDs saved to: {slo_output_file}")
    
    # Save full SLO configs for reference
    slo_config_file = f"{output_dir}/slos.json"
    with open(slo_config_file, "w") as f:
        json.dump(slos, f, indent=2)
    print(f"💾 Full SLO configs saved to: {slo_config_file}")
    
    print()
    print("=" * 60)
    print("📋 SLO Tier Summary")
    print("=" * 60)
    print("""
┌─────────────────────────────────────────────────────────────┐
│                    SLO TIER OVERVIEW                        │
├──────────┬──────────────────────────────┬───────────────────┤
│   Tier   │         Services             │   Error Budget    │
├──────────┼──────────────────────────────┼───────────────────┤
│  Tier 1  │ Frontend, Checkout, Payment  │  43.2 min/month   │
│ (99.9%)  │ (Revenue Critical)           │  (0.1% downtime)  │
├──────────┼──────────────────────────────┼───────────────────┤
│  Tier 2  │ Chatbot, Catalog, Cart       │  3.6 hrs/month    │
│ (99.5%)  │ (User Experience)            │  (0.5% downtime)  │
├──────────┼──────────────────────────────┼───────────────────┤
│  Tier 3  │ Recommendations, Ads, Email  │  7.2 hrs/month    │
│  (99%)   │ (Supporting)                 │  (1% downtime)    │
└──────────┴──────────────────────────────┴───────────────────┘
    """)
    
    return len(failed_slos) == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
