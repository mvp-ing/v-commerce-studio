#!/usr/bin/env python
"""
Observability Insights Agent - ADK-based agent with tools

This module implements an AI agent using Google's ADK (Agent Development Kit)
that can analyze observability data from Datadog and provide intelligent insights.

Tools available to the agent:
- query_datadog_metrics: Fetch metrics from Datadog
- get_quick_health_check: Rule-based health check (no LLM cost)
- get_llm_token_usage: Get token usage by service
- get_error_metrics: Get error rate and trends
- send_datadog_event: Send events to Datadog
- emit_datadog_metric: Emit custom metrics to Datadog
"""

import os
import logging
import json
import re
import time
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

# Set up Vertex AI environment BEFORE importing ADK
# This tells google-genai to use Vertex AI instead of AI Studio
os.environ.setdefault('GOOGLE_GENAI_USE_VERTEXAI', 'true')

import vertexai
from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# ============================================
# Datadog APM Setup
# ============================================
from ddtrace import tracer, patch_all, config
from ddtrace.llmobs import LLMObs

config.service = "observability-insights-agent"
patch_all()

LLMObs.enable(
    ml_app=os.getenv("DD_LLMOBS_ML_APP", "v-commerce-observability-agent"),
    agentless_enabled=os.getenv("DD_LLMOBS_AGENTLESS_ENABLED", "true").lower() == "true",
)

# ============================================

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "severity": "%(levelname)s", "service": "observability-insights-agent", "message": "%(message)s", "dd.trace_id": "%(dd.trace_id)s", "dd.span_id": "%(dd.span_id)s"}',
    datefmt='%Y-%m-%dT%H:%M:%S.%fZ'
)
logger = logging.getLogger(__name__)

# ============================================
# Global clients (initialized in ObservabilityAgent)
# ============================================
_datadog_client = None
_alert_sender = None


# ============================================
# TOOL FUNCTIONS (These are exposed to the LLM Agent)
# ============================================

def query_datadog_metrics(
    metric_name: str = "llm.request.duration",
    service: str = "*",
    time_window_hours: int = 1,
    aggregation: str = "avg"
) -> dict:
    """Query time-series metrics from Datadog.
    
    Args:
        metric_name: The metric to query (e.g., llm.request.duration, llm.tokens.input)
        service: Filter by service name, use * for all services
        time_window_hours: How many hours of data to fetch (1-24)
        aggregation: How to aggregate (avg, sum, max, min)
    
    Returns:
        dict with status, latest value, average, trend, and time series data
    """
    if _datadog_client is None:
        return {"status": "error", "error_message": "Datadog client not initialized"}
    
    try:
        service_filter = f"service:{service}" if service != "*" else "*"
        query = f"{aggregation}:{metric_name}{{{service_filter}}}"
        
        to_time = int(time.time())
        from_time = to_time - (time_window_hours * 3600)
        
        result = _datadog_client.query_metrics(query, from_time, to_time)
        
        if result and result.get("series"):
            series = result["series"][0]
            points = series.get("pointlist", [])
            values = [p[1] for p in points if p[1] is not None]
            
            return {
                "status": "success",
                "metric": metric_name,
                "service": service,
                "latest": values[-1] if values else None,
                "average": sum(values) / len(values) if values else None,
                "max": max(values) if values else None,
                "min": min(values) if values else None,
                "trend": _calculate_trend(values),
                "data_points": len(values)
            }
        return {"status": "success", "metric": metric_name, "message": "No data available"}
    except Exception as e:
        logger.error(f"Error querying metrics: {e}")
        return {"status": "error", "error_message": str(e)}


def get_quick_health_check() -> dict:
    """Perform a quick rule-based health check on all LLM services.
    
    This is a FREE operation (no LLM tokens used). Use this first to determine
    if a deeper AI analysis is needed.
    
    Returns:
        dict with overall health status, any concerns, and raw metrics
    """
    if _datadog_client is None:
        return {"status": "error", "error_message": "Datadog client not initialized"}
    
    try:
        result = _datadog_client.get_quick_health_check()
        return {
            "status": "success",
            "needs_deep_analysis": result.get("needs_deep_analysis", False),
            "concerns": result.get("concerns", []),
            "metrics": result.get("metrics", {}),
            "recommendation": "Run deep analysis" if result.get("needs_deep_analysis") else "System healthy, no action needed"
        }
    except Exception as e:
        logger.error(f"Error in quick health check: {e}")
        return {"status": "error", "error_message": str(e)}


def get_llm_token_usage(time_window_hours: int = 24) -> dict:
    """Get LLM token usage from Datadog LLM Observability metrics.
    
    This queries ml_obs.span.llm.* metrics that are automatically generated
    by Datadog from LLM spans.
    
    Args:
        time_window_hours: How many hours of data to aggregate (1-24)
    
    Returns:
        dict with token counts, costs, and LLM call counts
    """
    if _datadog_client is None:
        return {"status": "error", "error_message": "Datadog client not initialized"}
    
    try:
        usage = _datadog_client.get_token_usage_by_service(time_window_hours)
        
        # Get the aggregated data
        all_data = usage.get("all_services", {})
        
        output_tokens = all_data.get("output_tokens", 0)
        input_cost = all_data.get("input_cost_usd", 0)
        span_count = all_data.get("span_count", 0)
        total_cost = all_data.get("cost_usd_total", 0)
        estimated_input_tokens = all_data.get("estimated_input_tokens", 0)
        
        return {
            "status": "success",
            "data_source": "datadog_llm_observability",
            "time_window_hours": time_window_hours,
            "output_tokens": output_tokens,
            "estimated_input_tokens": estimated_input_tokens,
            "total_tokens_estimated": estimated_input_tokens + output_tokens,
            "llm_calls": span_count,
            "input_cost_usd": round(input_cost, 6),
            "total_cost_usd": round(total_cost, 6),
            "projected_daily_cost": round(total_cost * (24 / max(time_window_hours, 1)), 4),
            "projected_monthly_cost": round(total_cost * (24 / max(time_window_hours, 1)) * 30, 2)
        }
    except Exception as e:
        logger.error(f"Error getting token usage: {e}")
        return {"status": "error", "error_message": str(e)}


def get_error_metrics(time_window_hours: int = 1) -> dict:
    """Get error-related metrics for all services.
    
    Args:
        time_window_hours: How many hours of data to fetch
    
    Returns:
        dict with error rates, latencies, and trends for each service
    """
    if _datadog_client is None:
        return {"status": "error", "error_message": "Datadog client not initialized"}
    
    try:
        metrics = _datadog_client.get_error_metrics(time_window_hours)
        
        # Summarize concerns
        concerns = []
        for name, data in metrics.items():
            if data.get("trend") == "increasing":
                concerns.append(f"{name} is trending upward")
            if "error" in name.lower() and data.get("latest", 0) > 0.01:
                concerns.append(f"{name} is elevated at {data.get('latest'):.2%}")
        
        return {
            "status": "success",
            "time_window_hours": time_window_hours,
            "metrics": metrics,
            "concerns": concerns,
            "overall_health": "concerning" if concerns else "healthy"
        }
    except Exception as e:
        logger.error(f"Error getting error metrics: {e}")
        return {"status": "error", "error_message": str(e)}


def get_full_llm_metrics(service: str = "*", time_window_hours: int = 24) -> dict:
    """Get comprehensive LLM metrics for analysis.
    
    Args:
        service: Filter by service name, use * for all services
        time_window_hours: How many hours of data to fetch
    
    Returns:
        dict with all LLM-related metrics (latency, tokens, quality, etc.)
    """
    if _datadog_client is None:
        return {"status": "error", "error_message": "Datadog client not initialized"}
    
    try:
        metrics = _datadog_client.get_llm_metrics(service, time_window_hours)
        return {
            "status": "success",
            "service": service,
            "time_window_hours": time_window_hours,
            "metrics": metrics
        }
    except Exception as e:
        logger.error(f"Error getting LLM metrics: {e}")
        return {"status": "error", "error_message": str(e)}


def send_datadog_event(
    title: str,
    text: str,
    alert_type: str = "info",
    tags: str = ""
) -> dict:
    """Send an event to Datadog for visibility on dashboards.
    
    Args:
        title: Event title (short, descriptive)
        text: Event body (supports markdown)
        alert_type: One of: info, warning, error, success
        tags: Comma-separated tags (e.g., "prediction:error,severity:high")
    
    Returns:
        dict with status of the event submission
    """
    if _alert_sender is None:
        return {"status": "error", "error_message": "Alert sender not initialized"}
    
    try:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        success = _alert_sender.send_event(title, text, alert_type, "normal", tag_list)
        return {
            "status": "success" if success else "failed",
            "message": f"Event '{title}' sent to Datadog" if success else "Failed to send event"
        }
    except Exception as e:
        logger.error(f"Error sending event: {e}")
        return {"status": "error", "error_message": str(e)}


def emit_datadog_metric(
    metric_name: str,
    value: float,
    tags: str = ""
) -> dict:
    """Emit a custom metric to Datadog.
    
    Args:
        metric_name: Name of the metric (e.g., llm.prediction.error_probability)
        value: Numeric value for the metric
        tags: Comma-separated tags
    
    Returns:
        dict with status of the metric submission
    """
    if _alert_sender is None:
        return {"status": "error", "error_message": "Alert sender not initialized"}
    
    try:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        success = _alert_sender.emit_metric(metric_name, value, "gauge", tag_list)
        return {
            "status": "success" if success else "failed",
            "message": f"Metric {metric_name}={value} emitted" if success else "Failed to emit metric"
        }
    except Exception as e:
        logger.error(f"Error emitting metric: {e}")
        return {"status": "error", "error_message": str(e)}


def _calculate_trend(values: List[float]) -> str:
    """Calculate trend from values list"""
    if len(values) < 2:
        return "stable"
    mid = len(values) // 2
    first_avg = sum(values[:mid]) / max(mid, 1)
    second_avg = sum(values[mid:]) / max(len(values) - mid, 1)
    if first_avg == 0:
        return "stable" if second_avg == 0 else "increasing"
    change = (second_avg - first_avg) / first_avg
    if change > 0.2:
        return "increasing"
    elif change < -0.2:
        return "decreasing"
    return "stable"


# ============================================
# OBSERVABILITY AGENT CLASS
# ============================================

class ObservabilityAgent:
    """ADK-based Observability Insights Agent"""
    
    AGENT_INSTRUCTION = """You are an expert SRE and observability analyst for an e-commerce platform called Online Boutique. 
The platform has several LLM-powered services:
- chatbotservice: Customer support chatbot using Gemini
- shoppingassistantservice: Product recommendations using Gemini
- peau_agent: Proactive engagement agent using Gemini

Your job is to:
1. Monitor the health of these services using the available tools
2. Predict potential errors before they happen
3. Suggest cost optimization strategies for LLM token usage
4. Generate actionable insights for the engineering team

IMPORTANT WORKFLOW:
1. Always start with get_quick_health_check() - it's FREE (no LLM tokens)
2. Only dig deeper if concerns are found
3. When you identify issues, send events to Datadog using send_datadog_event
4. Emit prediction metrics using emit_datadog_metric

When analyzing:
- Look for trends, not just current values
- Consider the business impact of issues
- Provide specific, actionable recommendations
- Include confidence levels in your predictions

For cost optimization:
- Calculate cost per service
- Identify services with high token usage
- Suggest practical optimizations (caching, prompt optimization, model tiering)
"""
    
    def __init__(self, project_id: str = None, location: str = "us-central1"):
        global _datadog_client, _alert_sender
        
        self.project_id = project_id or os.getenv('PROJECT_ID', 'v-commerce-480915')
        self.location = location or os.getenv('LOCATION', 'us-central1')
        self.app_name = "observability_insights_agent"
        
        # Initialize Vertex AI FIRST (required for ADK)
        try:
            vertexai.init(project=self.project_id, location=self.location)
            logger.info(f"Vertex AI initialized (project: {self.project_id}, location: {self.location})")
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI: {e}")
            raise
        
        # Initialize Datadog clients
        from datadog_client import DatadogClient
        from alert_sender import AlertSender
        
        _datadog_client = DatadogClient()
        _alert_sender = AlertSender()
        
        # Initialize ADK Agent with tools
        # Note: After vertexai.init(), ADK will use Vertex AI automatically
        self.agent = LlmAgent(
            model="gemini-2.0-flash",
            name="observability_insights_agent",
            instruction=self.AGENT_INSTRUCTION,
            tools=[
                query_datadog_metrics,
                get_quick_health_check,
                get_llm_token_usage,
                get_error_metrics,
                get_full_llm_metrics,
                send_datadog_event,
                emit_datadog_metric
            ]
        )
        
        self.session_service = InMemorySessionService()
        logger.info("ObservabilityAgent initialized with 7 tools")
    
    async def analyze(self, task: str, user_id: str = "system") -> Dict[str, Any]:
        """Run the agent to analyze a specific task.
        
        Args:
            task: What analysis to perform (e.g., "Check system health", "Predict errors")
            user_id: User/session identifier
        
        Returns:
            dict with the agent's analysis and any actions taken
        """
        start_time = time.time()
        session_id = f"session_{user_id}_{int(time.time())}"
        
        with LLMObs.agent(
            name="observability_agent.analyze",
            ml_app="v-commerce-observability-agent"
        ) as agent_span:
            LLMObs.annotate(span=agent_span, input_data=task)
            
            try:
                # Create session
                await self.session_service.create_session(
                    app_name=self.app_name,
                    user_id=user_id,
                    session_id=session_id
                )
                
                # Create runner
                runner = Runner(
                    agent=self.agent,
                    app_name=self.app_name,
                    session_service=self.session_service
                )
                
                # Run agent
                user_content = types.Content(role='user', parts=[types.Part(text=task)])
                
                response_text = ""
                tool_calls = []
                
                async for event in runner.run_async(
                    user_id=user_id,
                    session_id=session_id,
                    new_message=user_content
                ):
                    logger.info(f"Agent event: {type(event).__name__}")
                    
                    # Track tool calls
                    if hasattr(event, 'tool_calls') and event.tool_calls:
                        for tc in event.tool_calls:
                            tool_calls.append(getattr(tc, 'name', str(tc)))
                    
                    # Get final response
                    if event.is_final_response() and event.content and event.content.parts:
                        response_text = event.content.parts[0].text.strip()
                        break
                
                duration_ms = (time.time() - start_time) * 1000
                
                LLMObs.annotate(
                    span=agent_span,
                    output_data=response_text,
                    metadata={"tool_calls": tool_calls, "duration_ms": duration_ms}
                )
                
                logger.info(f"Agent analysis complete: {len(tool_calls)} tool calls, {duration_ms:.0f}ms")
                
                return {
                    "status": "success",
                    "task": task,
                    "response": response_text,
                    "tool_calls": tool_calls,
                    "duration_ms": duration_ms
                }
                
            except Exception as e:
                logger.error(f"Agent analysis failed: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return {
                    "status": "error",
                    "task": task,
                    "error": str(e)
                }
    
    def analyze_sync(self, task: str, user_id: str = "system") -> Dict[str, Any]:
        """Synchronous wrapper for analyze()"""
        return asyncio.run(self.analyze(task, user_id))
    
    # Predefined analysis tasks
    def predict_errors(self) -> Dict[str, Any]:
        """Run error prediction analysis"""
        task = """Analyze the current system health and predict potential errors:

1. First, run get_quick_health_check() to see if there are any immediate concerns
2. If concerns exist, dig deeper with get_error_metrics() and get_full_llm_metrics()
3. Analyze trends and patterns
4. Calculate the probability of service degradation in the next 2 hours
5. Emit the prediction metric using emit_datadog_metric with metric name "llm.prediction.error_probability"
6. If probability > 50%, send a warning event to Datadog

Provide your analysis with:
- Probability of issues (0-100%)
- Root cause if probability is high
- Specific recommended actions
"""
        return self.analyze_sync(task)
    
    def analyze_costs(self) -> Dict[str, Any]:
        """Run cost optimization analysis"""
        task = """Analyze LLM token usage and suggest cost optimizations:

1. Use get_llm_token_usage() to get the last 24 hours of token usage
2. Identify which services are using the most tokens
3. Calculate daily and monthly projected costs
4. Suggest specific optimizations like:
   - Response caching opportunities
   - Prompt optimization (shorter prompts)
   - Model tiering (cheaper models for simple tasks)
5. Send a summary event to Datadog with your findings

Provide:
- Current daily cost
- Projected monthly cost
- Top 3 optimization recommendations with estimated savings
"""
        return self.analyze_sync(task)
    
    def generate_health_summary(self) -> Dict[str, Any]:
        """Generate a health summary"""
        task = """Generate a brief health summary for the engineering team:

1. Run get_quick_health_check() for immediate status
2. Check get_error_metrics() for recent trends
3. Summarize in 2-3 sentences

Format:
- Overall status: healthy/warning/critical
- Key highlights (what's working well)
- Any concerns (what needs attention)
- One actionable recommendation
"""
        return self.analyze_sync(task)


# ============================================
# MAIN (for testing)
# ============================================

if __name__ == "__main__":
    import asyncio
    
    async def test_agent():
        agent = ObservabilityAgent()
        
        # Test health check
        print("\n=== Testing Health Summary ===")
        result = await agent.analyze("Check the overall system health and give me a brief summary")
        print(f"Response: {result.get('response', 'No response')}")
        print(f"Tool calls: {result.get('tool_calls', [])}")
    
    asyncio.run(test_agent())
