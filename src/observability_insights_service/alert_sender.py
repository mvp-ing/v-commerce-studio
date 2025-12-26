#!/usr/bin/env python
"""
Alert Sender - Sends events and metrics TO Datadog

This module handles all WRITE operations to Datadog, including:
- Sending custom events (predictions, insights)
- Emitting custom metrics
- Creating incidents (optional)
"""

import os
import time
import logging
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)


class AlertSender:
    """Client for sending events and metrics to Datadog"""

    def __init__(self):
        """
        Initialize Alert Sender with API credentials.
        
        Required environment variables:
        - DD_API_KEY: Datadog API key
        - DD_SITE: Datadog site (e.g., us5.datadoghq.com)
        """
        self.api_key = os.getenv('DD_API_KEY')
        self.site = os.getenv('DD_SITE', 'us5.datadoghq.com')
        
        if not self.api_key:
            logger.warning("DD_API_KEY not set - Datadog writes will fail")
        
        self.base_url = f"https://api.{self.site}/api"
        
        self.headers = {
            "DD-API-KEY": self.api_key or "",
            "Content-Type": "application/json"
        }
        
        # Default tags for all events/metrics from this service
        self.default_tags = [
            "service:observability-insights-service",
            f"env:{os.getenv('DD_ENV', 'hackathon')}",
            "source:ai-insights"
        ]
        
        logger.info(f"AlertSender initialized for site: {self.site}")

    def _make_request(self, method: str, endpoint: str, json_data: Dict) -> bool:
        """Make an authenticated request to Datadog API"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=json_data,
                timeout=30
            )
            response.raise_for_status()
            logger.info(f"Successfully sent to {endpoint}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Datadog API request failed: {e}")
            return False

    def send_event(
        self,
        title: str,
        text: str,
        alert_type: str = "info",
        priority: str = "normal",
        tags: List[str] = None,
        aggregation_key: str = None
    ) -> bool:
        """
        Send an event to Datadog.
        
        Args:
            title: Event title
            text: Event body (supports markdown)
            alert_type: "error", "warning", "info", or "success"
            priority: "normal" or "low"
            tags: Additional tags for the event
            aggregation_key: Key to group related events
            
        Returns:
            True if successful, False otherwise
        """
        all_tags = self.default_tags.copy()
        if tags:
            all_tags.extend(tags)
        
        event_data = {
            "title": title,
            "text": text,
            "alert_type": alert_type,
            "priority": priority,
            "tags": all_tags,
            "source_type_name": "observability_insights",
            "date_happened": int(time.time())
        }
        
        if aggregation_key:
            event_data["aggregation_key"] = aggregation_key
        
        return self._make_request("POST", "/v1/events", event_data)

    def emit_metric(
        self,
        metric_name: str,
        value: float,
        metric_type: str = "gauge",
        tags: List[str] = None
    ) -> bool:
        """
        Emit a custom metric to Datadog.
        
        Args:
            metric_name: Name of the metric (e.g., "llm.prediction.error_probability")
            value: Numeric value
            metric_type: "gauge", "count", or "rate"
            tags: Additional tags for the metric
            
        Returns:
            True if successful, False otherwise
        """
        all_tags = self.default_tags.copy()
        if tags:
            all_tags.extend(tags)
        
        # Use v2 API for metrics submission
        metric_data = {
            "series": [
                {
                    "metric": metric_name,
                    "type": 1 if metric_type == "gauge" else 0,  # 1 = gauge, 0 = count
                    "points": [
                        {
                            "timestamp": int(time.time()),
                            "value": value
                        }
                    ],
                    "tags": all_tags
                }
            ]
        }
        
        return self._make_request("POST", "/v2/series", metric_data)

    def send_error_prediction(
        self,
        probability: float,
        cause: str,
        recommended_actions: List[str],
        affected_services: List[str] = None,
        time_to_issue_hours: float = 2.0
    ) -> bool:
        """
        Send an error prediction event and emit the prediction metric.
        
        Args:
            probability: Probability of error (0-1)
            cause: Root cause analysis
            recommended_actions: List of suggested actions
            affected_services: List of services that may be affected
            time_to_issue_hours: Estimated time until issue occurs
            
        Returns:
            True if successful
        """
        # Emit the probability metric
        self.emit_metric(
            "llm.prediction.error_probability",
            probability,
            metric_type="gauge",
            tags=[f"prediction_type:error"]
        )
        
        # Only send event if probability is concerning
        if probability < 0.5:
            logger.info(f"Error probability low ({probability:.2%}), not sending alert event")
            return True
        
        # Determine alert type based on probability
        if probability >= 0.8:
            alert_type = "error"
            emoji = "🚨"
        elif probability >= 0.6:
            alert_type = "warning"
            emoji = "⚠️"
        else:
            alert_type = "info"
            emoji = "ℹ️"
        
        # Format the event
        services_text = ", ".join(affected_services) if affected_services else "All LLM services"
        actions_text = "\n".join([f"- {action}" for action in recommended_actions])
        
        title = f"{emoji} Predicted Service Degradation ({probability:.0%} confidence)"
        
        text = f"""
## AI-Powered Prediction Alert

**Probability:** {probability:.1%}
**Estimated Time to Issue:** {time_to_issue_hours:.1f} hours
**Affected Services:** {services_text}

### Root Cause Analysis
{cause}

### Recommended Actions
{actions_text}

---
*This prediction was generated by the Observability Insights Service using Gemini AI analysis of telemetry patterns.*
"""
        
        return self.send_event(
            title=title,
            text=text,
            alert_type=alert_type,
            priority="normal",
            tags=["prediction:error", f"confidence:{probability:.2f}"],
            aggregation_key="error_prediction"
        )

    def send_cost_optimization_report(
        self,
        current_daily_cost: float,
        projected_monthly_cost: float,
        potential_savings: float,
        recommendations: List[Dict[str, Any]]
    ) -> bool:
        """
        Send a cost optimization report event.
        
        Args:
            current_daily_cost: Current daily LLM cost
            projected_monthly_cost: Projected monthly cost
            potential_savings: Potential monthly savings
            recommendations: List of optimization recommendations
            
        Returns:
            True if successful
        """
        # Emit cost metrics
        self.emit_metric("llm.prediction.cost_forecast_24h", current_daily_cost)
        self.emit_metric("llm.optimization.potential_savings", potential_savings)
        self.emit_metric("llm.cost.projected_monthly", projected_monthly_cost)
        
        # Format recommendations
        rec_text = ""
        for i, rec in enumerate(recommendations, 1):
            title = rec.get("title", "Optimization")
            description = rec.get("description", "")
            savings = rec.get("estimated_savings", 0)
            rec_text += f"\n### {i}. {title}\n{description}\n**Estimated Monthly Savings:** ${savings:.2f}\n"
        
        title = f"💰 LLM Cost Optimization Report"
        
        text = f"""
## Daily Cost Analysis

| Metric | Value |
|--------|-------|
| Current Daily Cost | ${current_daily_cost:.2f} |
| Projected Monthly Cost | ${projected_monthly_cost:.2f} |
| Potential Monthly Savings | ${potential_savings:.2f} ({(potential_savings/max(projected_monthly_cost, 0.01)*100):.1f}%) |

## Optimization Recommendations
{rec_text}

---
*This report was generated by the Observability Insights Service using Gemini AI analysis of token usage patterns.*
"""
        
        return self.send_event(
            title=title,
            text=text,
            alert_type="info",
            priority="low",
            tags=["report:cost_optimization"],
            aggregation_key="cost_report"
        )

    def send_health_summary(
        self,
        overall_status: str,
        summary_text: str,
        highlights: List[str] = None,
        concerns: List[str] = None,
        recommendations: List[str] = None
    ) -> bool:
        """
        Send a health summary event.
        
        Args:
            overall_status: "healthy", "warning", or "critical"
            summary_text: AI-generated summary text
            highlights: Positive highlights
            concerns: Areas of concern
            recommendations: Suggested actions
            
        Returns:
            True if successful
        """
        # Map status to alert type and emoji
        status_map = {
            "healthy": ("success", "🟢"),
            "warning": ("warning", "🟡"),
            "critical": ("error", "🔴")
        }
        alert_type, emoji = status_map.get(overall_status, ("info", "⚪"))
        
        # Format lists
        highlights_text = "\n".join([f"- {h}" for h in (highlights or [])])
        concerns_text = "\n".join([f"- {c}" for c in (concerns or [])])
        recommendations_text = "\n".join([f"- {r}" for r in (recommendations or [])])
        
        title = f"{emoji} System Health Summary - {overall_status.upper()}"
        
        text = f"""
## AI-Generated Health Summary

{summary_text}

### 📈 Highlights
{highlights_text if highlights_text else "- No significant highlights"}

### ⚠️ Concerns
{concerns_text if concerns_text else "- No current concerns"}

### 💡 Recommendations
{recommendations_text if recommendations_text else "- Continue monitoring"}

---
*Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by Observability Insights Service*
"""
        
        return self.send_event(
            title=title,
            text=text,
            alert_type=alert_type,
            priority="normal" if overall_status != "healthy" else "low",
            tags=[f"health:{overall_status}"],
            aggregation_key="health_summary"
        )

    def send_insights_generated_event(self, insight_type: str, success: bool = True) -> bool:
        """Track when insights are generated (for monitoring the service itself)"""
        self.emit_metric(
            "llm.insights.generated",
            1 if success else 0,
            metric_type="count",
            tags=[f"insight_type:{insight_type}", f"success:{str(success).lower()}"]
        )
        return True
