#!/usr/bin/env python
"""
Datadog Client - Fetches metrics from Datadog Metrics API

This module handles all READ operations from Datadog, including:
- Querying time-series metrics
- Fetching LLM-specific metrics (tokens, latency, errors)
- Aggregating data for analysis
"""

import os
import time
import logging
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)


class DatadogClient:
    """Client for reading metrics from Datadog Metrics API"""

    def __init__(self):
        """
        Initialize Datadog client with API credentials.
        
        Required environment variables:
        - DD_API_KEY: Datadog API key
        - DD_APP_KEY: Datadog Application key (required for querying metrics)
        - DD_SITE: Datadog site (e.g., us5.datadoghq.com)
        """
        self.api_key = os.getenv('DD_API_KEY')
        self.app_key = os.getenv('DD_APP_KEY')
        self.site = os.getenv('DD_SITE', 'us5.datadoghq.com')
        
        # Validate credentials
        if not self.api_key:
            logger.warning("DD_API_KEY not set - Datadog queries will fail")
        if not self.app_key:
            logger.warning("DD_APP_KEY not set - Datadog queries will fail")
        
        # Base URL for Datadog API
        self.base_url = f"https://api.{self.site}/api"
        
        # Common headers for API requests
        self.headers = {
            "DD-API-KEY": self.api_key or "",
            "DD-APPLICATION-KEY": self.app_key or "",
            "Content-Type": "application/json"
        }
        
        logger.info(f"DatadogClient initialized for site: {self.site}")

    def _make_request(self, method: str, endpoint: str, params: Dict = None, json_data: Dict = None) -> Optional[Dict]:
        """Make an authenticated request to Datadog API"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=json_data,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Datadog API request failed: {e}")
            return None

    def query_metrics(self, query: str, from_time: int = None, to_time: int = None) -> Optional[Dict]:
        """
        Query time-series metrics from Datadog.
        
        Args:
            query: Datadog metrics query (e.g., "avg:llm.request.duration{service:chatbotservice}")
            from_time: Start time as Unix timestamp (default: 1 hour ago)
            to_time: End time as Unix timestamp (default: now)
            
        Returns:
            Dict with series data or None if failed
        """
        if to_time is None:
            to_time = int(time.time())
        if from_time is None:
            from_time = to_time - 3600  # 1 hour ago
        
        params = {
            "query": query,
            "from": from_time,
            "to": to_time
        }
        
        result = self._make_request("GET", "/v1/query", params=params)
        
        if result and "series" in result:
            logger.info(f"Query returned {len(result['series'])} series")
            return result
        
        logger.warning(f"Query returned no series: {query}")
        return result

    def get_llm_metrics(self, service: str = "*", time_window_hours: int = 24) -> Dict[str, Any]:
        """
        Fetch all LLM-related metrics for a service.
        
        Args:
            service: Service name filter (default: all services)
            time_window_hours: How many hours of data to fetch
            
        Returns:
            Dict containing aggregated LLM metrics
        """
        to_time = int(time.time())
        from_time = to_time - (time_window_hours * 3600)
        
        service_filter = f"service:{service}" if service != "*" else "*"
        
        metrics = {}
        
        # Query key LLM metrics
        metric_queries = {
            "request_duration": f"avg:llm.request.duration{{{service_filter}}}",
            "tokens_input": f"sum:llm.tokens.input{{{service_filter}}}.as_count()",
            "tokens_output": f"sum:llm.tokens.output{{{service_filter}}}.as_count()",
            "total_cost": f"sum:llm.tokens.total_cost_usd{{{service_filter}}}",
            "quality_score": f"avg:llm.response.quality_score{{{service_filter}}}",
            "invalid_product_rate": f"avg:llm.recommendation.invalid_product_rate{{{service_filter}}}",
            "error_rate": f"avg:llm.error.rate{{{service_filter}}}"
        }
        
        for metric_name, query in metric_queries.items():
            result = self.query_metrics(query, from_time, to_time)
            if result and result.get("series"):
                # Extract point values from the series
                series = result["series"][0]
                points = series.get("pointlist", [])
                if points:
                    # Get latest value and time series
                    metrics[metric_name] = {
                        "latest": points[-1][1] if points else None,
                        "series": [{"timestamp": p[0], "value": p[1]} for p in points],
                        "avg": sum(p[1] for p in points if p[1] is not None) / max(len(points), 1)
                    }
                else:
                    metrics[metric_name] = {"latest": None, "series": [], "avg": None}
            else:
                metrics[metric_name] = {"latest": None, "series": [], "avg": None}
        
        logger.info(f"Fetched LLM metrics for {service}: {list(metrics.keys())}")
        return metrics

    def get_error_metrics(self, time_window_hours: int = 1) -> Dict[str, Any]:
        """
        Fetch error-related metrics for prediction.
        
        Args:
            time_window_hours: How many hours of data to fetch
            
        Returns:
            Dict containing error metrics and trends
        """
        to_time = int(time.time())
        from_time = to_time - (time_window_hours * 3600)
        
        error_queries = {
            "chatbot_errors": "sum:trace.flask.request.errors{service:chatbotservice}.as_count()",
            "chatbot_latency_p99": "p99:trace.flask.request{service:chatbotservice}",
            "shopping_assistant_errors": "sum:trace.flask.request.errors{service:shoppingassistantservice}.as_count()",
            "peau_agent_errors": "sum:trace.flask.request.errors{service:peau_agent}.as_count()",
            "llm_error_rate": "avg:llm.error.rate{*}",
            "llm_latency": "avg:llm.request.duration{*}"
        }
        
        metrics = {}
        for name, query in error_queries.items():
            result = self.query_metrics(query, from_time, to_time)
            if result and result.get("series"):
                series = result["series"][0]
                points = series.get("pointlist", [])
                values = [p[1] for p in points if p[1] is not None]
                
                metrics[name] = {
                    "latest": values[-1] if values else 0,
                    "trend": self._calculate_trend(values),
                    "avg": sum(values) / max(len(values), 1) if values else 0,
                    "max": max(values) if values else 0
                }
            else:
                metrics[name] = {"latest": 0, "trend": "stable", "avg": 0, "max": 0}
        
        return metrics

    def get_token_usage_by_service(self, time_window_hours: int = 24) -> Dict[str, Dict]:
        """
        Get token usage breakdown using Datadog LLM Observability metrics.
        
        Available metrics from Datadog:
        - ml_obs.span.llm.completion.tokens (output tokens)
        - ml_obs.span.llm.input.characters (input in characters)
        - ml_obs.span.llm.input.cost (input cost)
        - ml_obs.span (count of spans)
        
        Args:
            time_window_hours: How many hours of data to aggregate
            
        Returns:
            Dict mapping ml_app to token usage stats
        """
        to_time = int(time.time())
        from_time = to_time - (time_window_hours * 3600)
        
        usage = {}
        
        # Query aggregated LLM metrics (without filter first to get all data)
        output_result = self.query_metrics(
            "sum:ml_obs.span.llm.completion.tokens{*}",
            from_time, to_time
        )
        input_cost_result = self.query_metrics(
            "sum:ml_obs.span.llm.input.cost{*}",
            from_time, to_time
        )
        span_count_result = self.query_metrics(
            "sum:ml_obs.span{*}.as_count()",
            from_time, to_time
        )
        
        output_tokens = self._get_total_from_result(output_result)
        input_cost = self._get_total_from_result(input_cost_result)
        span_count = self._get_total_from_result(span_count_result)
        
        # Estimate input tokens from cost (Gemini pricing: $0.075 per 1M input tokens)
        estimated_input_tokens = int((input_cost / 0.075) * 1_000_000) if input_cost > 0 else 0
        
        usage["all_services"] = {
            "output_tokens": output_tokens,
            "input_cost_usd": input_cost,
            "estimated_input_tokens": estimated_input_tokens,
            "total_tokens_estimated": estimated_input_tokens + output_tokens,
            "span_count": span_count,
            "cost_usd_total": input_cost + self._estimate_output_cost(int(output_tokens))
        }
        
        return usage
    
    def _estimate_output_cost(self, output_tokens: int) -> float:
        """Estimate output cost based on Gemini pricing ($0.30 per 1M output tokens)"""
        return (output_tokens / 1_000_000) * 0.30

    def get_quick_health_check(self) -> Dict[str, Any]:
        """
        Quick health check using simple threshold-based rules.
        Returns metrics that can be used to decide if deeper Gemini analysis is needed.
        
        This is the first level of the hybrid approach - FREE (no LLM call).
        """
        # Get last 15 minutes of data
        to_time = int(time.time())
        from_time = to_time - 900  # 15 minutes
        
        health = {
            "needs_deep_analysis": False,
            "concerns": [],
            "metrics": {}
        }
        
        # Check error rate
        error_result = self.query_metrics("avg:llm.error.rate{*}", from_time, to_time)
        if error_result and error_result.get("series"):
            points = error_result["series"][0].get("pointlist", [])
            if points:
                latest_error_rate = points[-1][1] if points[-1][1] is not None else 0
                health["metrics"]["error_rate"] = latest_error_rate
                if latest_error_rate > 0.02:  # 2% threshold
                    health["needs_deep_analysis"] = True
                    health["concerns"].append(f"Error rate elevated: {latest_error_rate:.2%}")
        
        # Check latency
        latency_result = self.query_metrics("avg:llm.request.duration{*}", from_time, to_time)
        if latency_result and latency_result.get("series"):
            points = latency_result["series"][0].get("pointlist", [])
            if points:
                latest_latency = points[-1][1] if points[-1][1] is not None else 0
                health["metrics"]["latency_avg"] = latest_latency
                if latest_latency > 3.0:  # 3 second threshold
                    health["needs_deep_analysis"] = True
                    health["concerns"].append(f"Latency elevated: {latest_latency:.2f}s")
        
        # Check hallucination rate
        hallucination_result = self.query_metrics("avg:llm.recommendation.invalid_product_rate{*}", from_time, to_time)
        if hallucination_result and hallucination_result.get("series"):
            points = hallucination_result["series"][0].get("pointlist", [])
            if points:
                latest_rate = points[-1][1] if points[-1][1] is not None else 0
                health["metrics"]["hallucination_rate"] = latest_rate
                if latest_rate > 0.02:  # 2% threshold
                    health["needs_deep_analysis"] = True
                    health["concerns"].append(f"Hallucination rate elevated: {latest_rate:.2%}")
        
        return health

    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from a list of values"""
        if len(values) < 2:
            return "stable"
        
        # Compare first half avg to second half avg
        mid = len(values) // 2
        first_half_avg = sum(values[:mid]) / max(mid, 1)
        second_half_avg = sum(values[mid:]) / max(len(values) - mid, 1)
        
        if first_half_avg == 0:
            return "stable" if second_half_avg == 0 else "increasing"
        
        change_ratio = (second_half_avg - first_half_avg) / first_half_avg
        
        if change_ratio > 0.2:
            return "increasing"
        elif change_ratio < -0.2:
            return "decreasing"
        else:
            return "stable"

    def _get_total_from_result(self, result: Optional[Dict]) -> float:
        """Extract total value from a query result"""
        if not result or not result.get("series"):
            return 0
        
        series = result["series"][0]
        points = series.get("pointlist", [])
        return sum(p[1] for p in points if p[1] is not None)

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Estimate cost based on Gemini 2.0 Flash pricing.
        Input: $0.075 per 1M tokens
        Output: $0.30 per 1M tokens
        """
        input_cost = (input_tokens / 1_000_000) * 0.075
        output_cost = (output_tokens / 1_000_000) * 0.30
        return input_cost + output_cost

    def validate_connection(self) -> bool:
        """Validate that we can connect to Datadog API"""
        try:
            result = self._make_request("GET", "/v1/validate")
            if result and result.get("valid"):
                logger.info("Datadog API connection validated successfully")
                return True
            else:
                logger.error("Datadog API validation failed")
                return False
        except Exception as e:
            logger.error(f"Datadog API validation error: {e}")
            return False

    # ============================================
    # LLM Observability API Methods (Traces/Spans)
    # ============================================
    
    def query_llm_spans(self, filter_query: str = "*", time_window_minutes: int = 15) -> Optional[Dict]:
        """
        Query LLM Observability spans from the Traces API.
        
        Args:
            filter_query: Filter query (e.g., "ml_app:v-commerce-chatbot")
            time_window_minutes: How many minutes to look back (default: 15)
        
        Returns:
            Dict with span data or None if failed
        """
        # Use relative time format that Datadog accepts
        from_time = f"now-{time_window_minutes}m"
        to_time = "now"
        
        # Correct request body format per Datadog API docs
        payload = {
            "data": {
                "type": "search_request",
                "attributes": {
                    "filter": {
                        "query": filter_query,
                        "from": from_time,
                        "to": to_time
                    },
                    "sort": "timestamp",
                    "page": {
                        "limit": 100
                    }
                }
            }
        }
        
        result = self._make_request("POST", "/v2/spans/events/search", json_data=payload)
        
        if result:
            spans = result.get("data", [])
            logger.info(f"LLM spans query returned {len(spans)} spans")
            return result
        
        logger.warning(f"LLM spans query returned no data for: {filter_query}")
        return None

    def get_llm_observability_summary(self, ml_app: str = "*", time_window_minutes: int = 60) -> Dict[str, Any]:
        """
        Get summary of LLM Observability data from spans.
        
        This queries the LLM Observability data that's visible in the 
        Datadog LLM Observability dashboard (Token Usage, Estimated Cost, etc.)
        
        Args:
            ml_app: ML application name filter (e.g., "v-commerce-chatbot")
            time_window_minutes: How many minutes to look back
        
        Returns:
            Dict with summary data including token usage, cost, and call counts
        """
        filter_query = f"ml_app:{ml_app}" if ml_app != "*" else "*"
        
        result = self.query_llm_spans(filter_query, time_window_minutes)
        
        summary = {
            "ml_app": ml_app,
            "time_window_minutes": time_window_minutes,
            "total_spans": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
            "estimated_cost_usd": 0,
            "avg_duration_ms": 0,
            "error_count": 0,
            "spans_by_service": {},
            "models_used": set()
        }
        
        if not result or not result.get("data"):
            logger.info("No LLM spans found")
            return summary
        
        spans = result.get("data", [])
        summary["total_spans"] = len(spans)
        
        durations = []
        
        for span in spans:
            attrs = span.get("attributes", {})
            
            # Extract token counts
            input_tokens = attrs.get("meta", {}).get("input_tokens", 0) or 0
            output_tokens = attrs.get("meta", {}).get("output_tokens", 0) or 0
            
            # Also try alternative attribute paths
            if input_tokens == 0:
                input_tokens = attrs.get("metrics", {}).get("input_tokens", 0) or 0
            if output_tokens == 0:
                output_tokens = attrs.get("metrics", {}).get("output_tokens", 0) or 0
            
            summary["total_input_tokens"] += input_tokens
            summary["total_output_tokens"] += output_tokens
            
            # Extract duration
            duration = attrs.get("duration", 0)
            if duration:
                durations.append(duration)
            
            # Track errors
            if attrs.get("status") == "error" or attrs.get("error"):
                summary["error_count"] += 1
            
            # Track service
            service = attrs.get("service", "unknown")
            if service not in summary["spans_by_service"]:
                summary["spans_by_service"][service] = 0
            summary["spans_by_service"][service] += 1
            
            # Track model
            model = attrs.get("meta", {}).get("model", attrs.get("model_name", "unknown"))
            if model:
                summary["models_used"].add(model)
        
        # Calculate totals
        summary["total_tokens"] = summary["total_input_tokens"] + summary["total_output_tokens"]
        summary["estimated_cost_usd"] = self._estimate_cost(
            summary["total_input_tokens"], 
            summary["total_output_tokens"]
        )
        summary["avg_duration_ms"] = sum(durations) / len(durations) / 1_000_000 if durations else 0
        summary["models_used"] = list(summary["models_used"])
        
        logger.info(f"LLM Observability summary: {summary['total_spans']} spans, {summary['total_tokens']} tokens, ${summary['estimated_cost_usd']:.4f}")
        
        return summary

    def get_llm_token_usage_from_spans(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """
        Get token usage from LLM Observability spans (not Metrics API).
        
        This is the method to use when you want data that matches the 
        LLM Observability dashboard in Datadog.
        
        Args:
            time_window_hours: How many hours to look back
        
        Returns:
            Dict with token usage summary
        """
        time_window_minutes = time_window_hours * 60
        
        # Query for all LLM apps we know about
        ml_apps = ["v-commerce-chatbot", "v-commerce-shopping-assistant", "v-commerce-peau-agent"]
        
        combined = {
            "time_window_hours": time_window_hours,
            "total_tokens": 0,
            "total_cost_usd": 0,
            "total_llm_calls": 0,
            "by_app": {}
        }
        
        for ml_app in ml_apps:
            summary = self.get_llm_observability_summary(ml_app, time_window_minutes)
            
            combined["total_tokens"] += summary["total_tokens"]
            combined["total_cost_usd"] += summary["estimated_cost_usd"]
            combined["total_llm_calls"] += summary["total_spans"]
            
            if summary["total_spans"] > 0:
                combined["by_app"][ml_app] = {
                    "tokens": summary["total_tokens"],
                    "cost_usd": summary["estimated_cost_usd"],
                    "llm_calls": summary["total_spans"],
                    "avg_duration_ms": summary["avg_duration_ms"],
                    "errors": summary["error_count"]
                }
        
        # Calculate projections
        hours_in_window = max(time_window_hours, 1)
        combined["projected_daily_cost"] = (combined["total_cost_usd"] / hours_in_window) * 24
        combined["projected_monthly_cost"] = combined["projected_daily_cost"] * 30
        
        return combined

