#!/usr/bin/env python3
"""
Datadog Infrastructure Dashboard Creator

This script creates the V-Commerce Infrastructure Metrics Dashboard using the Datadog API.
The dashboard provides comprehensive visibility into Kubernetes cluster health, 
container resources, and system metrics.

Dashboard Sections:
1. Cluster Overview - Nodes, pods, containers status
2. CPU & Memory - Resource utilization by service
3. Network Metrics - Network I/O and errors
4. Disk & Storage - Filesystem usage and I/O
5. Node Health - Host-level metrics
6. Infrastructure Alerts - Critical infrastructure KPIs

Usage:
    source .env.datadog
    python3 scripts/create-infra-dashboard.py

Requirements:
    pip install requests
    
Environment Variables:
    DD_API_KEY - Datadog API key
    DD_APP_KEY - Datadog Application key
    DD_SITE - Datadog site (default: us5.datadoghq.com)
"""

import os
import json
import requests
import sys
from typing import Dict, Any

# Datadog API configuration
DD_API_KEY = os.getenv("DD_API_KEY")
DD_APP_KEY = os.getenv("DD_APP_KEY")
DD_SITE = os.getenv("DD_SITE")


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
    url = f"https://api.{DD_SITE}/api/v1/validate"
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


def create_dashboard(dashboard_config: Dict[str, Any]) -> Dict[str, Any]:
    """Create a dashboard in Datadog."""
    url = f"https://api.{DD_SITE}/api/v1/dashboard"
    
    response = requests.post(url, headers=get_headers(), json=dashboard_config)
    return response.json()


def load_dashboard_from_file() -> Dict[str, Any]:
    """Load dashboard configuration from JSON file."""
    dashboard_path = os.path.join(
        os.path.dirname(__file__), 
        "..", 
        "datadog-exports", 
        "dashboards", 
        "infrastructure-metrics-dashboard.json"
    )
    
    with open(dashboard_path, "r") as f:
        return json.load(f)


def main():
    """Main function to create the infrastructure dashboard."""
    print("=" * 60)
    print("🖥️  V-Commerce Infrastructure Metrics Dashboard Creator")
    print("=" * 60)
    print()
    
    # Validate credentials
    if not validate_credentials():
        sys.exit(1)
    
    print()
    print("📊 Loading dashboard configuration...")
    
    # Load dashboard from JSON file
    try:
        dashboard_config = load_dashboard_from_file()
        print(f"✅ Loaded dashboard: {dashboard_config['title']}")
    except Exception as e:
        print(f"❌ Error loading dashboard file: {e}")
        sys.exit(1)
    
    print()
    print("🚀 Creating dashboard in Datadog...")
    
    # Create the dashboard
    result = create_dashboard(dashboard_config)
    
    if "id" in result:
        dashboard_id = result["id"]
        dashboard_url = f"https://app.{DD_SITE}/dashboard/{dashboard_id}"
        print()
        print("=" * 60)
        print("✅ SUCCESS! Infrastructure Dashboard created!")
        print("=" * 60)
        print()
        print(f"   Dashboard ID:  {dashboard_id}")
        print(f"   Dashboard URL: {dashboard_url}")
        print()
        print("📋 Dashboard Sections:")
        print("   • 🖥️  Cluster Overview - Nodes, pods, containers status")
        print("   • 💾 CPU & Memory - Resource utilization by service")
        print("   • 🌐 Network Metrics - Network I/O and errors")
        print("   • 💿 Disk & Storage - Filesystem usage and I/O")
        print("   • ⚙️  Node Health - Host-level metrics")
        print("   • 🚨 Infrastructure Alerts - Critical infrastructure KPIs")
        print()
        
        # Save the created dashboard info
        output_path = os.path.join(
            os.path.dirname(__file__), 
            "..", 
            "datadog-exports", 
            "created-infra-dashboard.json"
        )
        with open(output_path, "w") as f:
            json.dump({
                "id": dashboard_id,
                "url": dashboard_url,
                "title": dashboard_config["title"],
                "created_at": result.get("created_at", ""),
                "author_handle": result.get("author_handle", "")
            }, f, indent=2)
        print(f"💾 Dashboard info saved to: datadog-exports/created-infra-dashboard.json")
    else:
        print()
        print("❌ Error creating dashboard:")
        print(json.dumps(result, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
