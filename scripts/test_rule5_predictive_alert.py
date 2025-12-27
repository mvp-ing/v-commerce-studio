#!/usr/bin/env python3
"""
Test Script: Rule 5 - Predictive Capacity Alert (AI-Powered)

This script directly triggers the Predictive Capacity Alert by:
1. Emitting llm.prediction.error_probability metrics with the correct tags
2. Sending multiple data points to ensure sum > 0.8 threshold

Monitor Query:
    sum(last_30m):sum:llm.prediction.error_probability{env:hackathon,service:v-commerce}.as_count() > 0.8

Usage:
    source .env.datadog
    python3 scripts/test_rule5_predictive_alert.py
"""

import os
import sys
import time
import requests

# Required tags that match the Datadog monitor query
REQUIRED_TAGS = [
    "env:hackathon",
    "service:v-commerce"
]


def emit_metric_direct(api_key: str, site: str, metric_name: str, value: float, tags: list) -> bool:
    """Emit metric directly to Datadog API with specific tags.
    
    Using type 3 (gauge) - this is what works best with sum().as_count() queries.
    The .as_count() modifier converts gauge values to counts per interval.
    """
    url = f"https://api.{site}/api/v2/series"
    headers = {
        "DD-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    
    # Datadog v2 API metric types:
    # 0 = unspecified, 1 = count, 2 = rate, 3 = gauge
    payload = {
        "series": [{
            "metric": metric_name,
            "type": 3,  # gauge - will be converted by .as_count()
            "points": [{
                "timestamp": int(time.time()),
                "value": value
            }],
            "tags": tags
        }]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"   Error: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"   Response: {e.response.text}")
        return False


def verify_metric_exists(api_key: str, app_key: str, site: str, metric_name: str) -> dict:
    """Query Datadog to verify the metric exists and has recent data."""
    url = f"https://api.{site}/api/v1/query"
    headers = {
        "DD-API-KEY": api_key,
        "DD-APPLICATION-KEY": app_key,
        "Content-Type": "application/json"
    }
    
    # Query the last 10 minutes of data
    now = int(time.time())
    from_time = now - 600  # 10 minutes ago
    
    params = {
        "from": from_time,
        "to": now,
        "query": f"sum:{metric_name}{{env:hackathon,service:v-commerce}}"
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        print(f"   Verification error: {e}")
        return {}


def main():
    print("=" * 60)
    print("🎯 Testing Rule 5: Predictive Capacity Alert (AI-Powered)")
    print("=" * 60)
    
    api_key = os.getenv('DD_API_KEY')
    app_key = os.getenv('DD_APP_KEY')
    site = os.getenv('DD_SITE', 'datadoghq.com')
    
    if not api_key:
        print("❌ ERROR: DD_API_KEY not set!")
        print("   Run: source .env.datadog")
        sys.exit(1)
    
    print(f"✅ Datadog site: {site}")
    print(f"✅ API Key: {api_key[:8]}...{api_key[-4:]}")
    print(f"\n📋 Monitor Query:")
    print("   sum(last_30m):sum:llm.prediction.error_probability{env:hackathon,service:v-commerce}.as_count() > 0.8")
    
    # Tags that match the monitor query EXACTLY
    tags = REQUIRED_TAGS.copy()
    
    print(f"\n📊 Emitting metrics with tags: {tags}")
    
    # Emit multiple high-value metrics
    success_count = 0
    total_emissions = 10  # More emissions to ensure data shows up
    
    print(f"\n🚀 Emitting {total_emissions} data points (value=1.0 each)...")
    print(f"   (Using value=1.0 so sum will clearly exceed 0.8 threshold)")
    
    for i in range(total_emissions):
        result = emit_metric_direct(
            api_key=api_key,
            site=site,
            metric_name='llm.prediction.error_probability',
            value=1.0,  # Use 1.0 for clearer visibility
            tags=tags
        )
        if result:
            success_count += 1
            print(f"   [{i+1}/{total_emissions}] ✅ Emitted llm.prediction.error_probability = 1.0")
        else:
            print(f"   [{i+1}/{total_emissions}] ❌ Failed")
        
        # Delay between emissions to create distinct data points
        if i < total_emissions - 1:
            time.sleep(2)
    
    print(f"\n📈 Summary:")
    print(f"   - Emissions: {success_count}/{total_emissions} successful")
    print(f"   - Total value emitted: {1.0 * success_count:.2f}")
    print(f"   - Threshold: > 0.8")
    
    # Wait a bit for Datadog to process
    print(f"\n⏳ Waiting 30 seconds for Datadog to process metrics...")
    time.sleep(30)
    
    # Verify the metric exists
    if app_key:
        print(f"\n🔍 Verifying metric in Datadog...")
        result = verify_metric_exists(api_key, app_key, site, 'llm.prediction.error_probability')
        
        if result.get('series'):
            print(f"   ✅ Metric found! Data points: {len(result['series'][0].get('pointlist', []))}")
            points = result['series'][0].get('pointlist', [])
            if points:
                latest = points[-1]
                print(f"   Latest value: {latest[1]} at timestamp {latest[0]}")
        else:
            print(f"   ⚠️  No data returned from query")
            print(f"   Raw response: {result}")
    else:
        print(f"\n⚠️  DD_APP_KEY not set - cannot verify metric. Set it to enable verification.")
    
    print("\n" + "=" * 60)
    if success_count >= 1:
        print("✅ Rule 5: Metrics emitted to Datadog!")
        print("\n📍 Next steps:")
        print("   1. Go to Metrics Explorer in Datadog")
        print("   2. Search for: llm.prediction.error_probability")
        print("   3. Add filter: env:hackathon, service:v-commerce")
        print("   4. Check if data appears in the graph")
        print("\n   If no data appears, try changing the monitor query to:")
        print("   avg(last_5m):avg:llm.prediction.error_probability{env:hackathon,service:v-commerce} > 0.8")
    else:
        print("⚠️  All emissions failed. Check Datadog API connectivity.")
    print("=" * 60)


if __name__ == '__main__':
    main()

