#!/usr/bin/env python3
"""
Fetch all available metrics from Datadog and list them.
"""

import os
import json
import requests
from typing import Dict, List

# Datadog API configuration
DD_API_KEY = os.getenv("DD_API_KEY", "de8576d9b3ea8cd083ff20da7b3e7b1e")
DD_APP_KEY = os.getenv("DD_APP_KEY", "60c7b84e3af1680a8862b72f88f5370817bfbec1")
DD_SITE = os.getenv("DD_SITE", "us5.datadoghq.com")


def get_headers() -> Dict[str, str]:
    """Return headers for Datadog API requests."""
    return {
        "DD-API-KEY": DD_API_KEY,
        "DD-APPLICATION-KEY": DD_APP_KEY,
        "Content-Type": "application/json"
    }


def get_all_metrics() -> List[str]:
    """Fetch all available metrics from Datadog."""
    url = f"https://api.{DD_SITE}/api/v1/metrics"
    
    response = requests.get(url, headers=get_headers())
    if response.status_code == 200:
        data = response.json()
        return data.get("metrics", [])
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return []


def get_active_metrics(from_time: int = None) -> List[str]:
    """Fetch active metrics from the last hour."""
    import time
    if from_time is None:
        from_time = int(time.time()) - 3600  # Last hour
    
    url = f"https://api.{DD_SITE}/api/v1/metrics?from={from_time}"
    
    response = requests.get(url, headers=get_headers())
    if response.status_code == 200:
        data = response.json()
        return data.get("metrics", [])
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return []


def search_metrics(query: str) -> List[str]:
    """Search for metrics matching a query pattern."""
    url = f"https://api.{DD_SITE}/api/v1/search?q=metrics:{query}"
    
    response = requests.get(url, headers=get_headers())
    if response.status_code == 200:
        data = response.json()
        return data.get("results", {}).get("metrics", [])
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return []


def main():
    print("=" * 60)
    print("🔍 Fetching Available Metrics from Datadog")
    print("=" * 60)
    print()
    
    # Get all active metrics
    print("📊 Fetching active metrics from the last hour...")
    metrics = get_active_metrics()
    
    if not metrics:
        print("No metrics found in the last hour. Fetching all metrics...")
        metrics = get_all_metrics()
    
    print(f"\n✅ Found {len(metrics)} metrics\n")
    
    # Categorize metrics
    categories = {
        "kubernetes": [],
        "container": [],
        "docker": [],
        "system": [],
        "trace": [],
        "llm": [],
        "network": [],
        "disk": [],
        "cpu": [],
        "memory": [],
        "other": []
    }
    
    for metric in sorted(metrics):
        metric_lower = metric.lower()
        categorized = False
        
        for category in categories:
            if category in metric_lower:
                categories[category].append(metric)
                categorized = True
                break
        
        if not categorized:
            categories["other"].append(metric)
    
    # Print categorized metrics
    for category, metric_list in categories.items():
        if metric_list:
            print(f"\n{'='*60}")
            print(f"📁 {category.upper()} METRICS ({len(metric_list)})")
            print("="*60)
            for m in sorted(metric_list)[:50]:  # Limit to 50 per category
                print(f"  • {m}")
            if len(metric_list) > 50:
                print(f"  ... and {len(metric_list) - 50} more")
    
    # Save all metrics to file
    output_path = os.path.join(
        os.path.dirname(__file__), 
        "..", 
        "datadog-exports", 
        "available-metrics.json"
    )
    with open(output_path, "w") as f:
        json.dump({
            "total_count": len(metrics),
            "categories": {k: v for k, v in categories.items() if v},
            "all_metrics": sorted(metrics)
        }, f, indent=2)
    
    print(f"\n💾 Saved metrics list to: datadog-exports/available-metrics.json")
    
    # Search for specific infrastructure-related metrics
    print("\n" + "="*60)
    print("🔍 Searching for specific metric patterns...")
    print("="*60)
    
    patterns = ["kubernetes", "container", "system", "docker", "trace"]
    for pattern in patterns:
        results = search_metrics(pattern)
        print(f"\n'{pattern}': {len(results)} metrics found")
        for r in results[:10]:
            print(f"  • {r}")
        if len(results) > 10:
            print(f"  ... and {len(results) - 10} more")


if __name__ == "__main__":
    main()
