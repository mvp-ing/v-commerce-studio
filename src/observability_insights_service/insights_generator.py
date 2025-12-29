#!/usr/bin/env python
"""
Insights Generator - Gemini-powered analysis engine

This module is the AI brain of the Observability Insights Service.
It uses Gemini to analyze telemetry data and generate:
- Error predictions
- Cost optimization suggestions
- Health summaries
"""

import os
import json
import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

import vertexai
from vertexai.generative_models import GenerativeModel

from datadog_client import DatadogClient
from alert_sender import AlertSender

# Configure logging
logger = logging.getLogger(__name__)


class InsightsGenerator:
    """Gemini-powered observability insights generator"""

    def __init__(self, datadog_client: DatadogClient = None, alert_sender: AlertSender = None):
        """
        Initialize the insights generator.
        
        Args:
            datadog_client: Client for reading metrics from Datadog
            alert_sender: Client for sending events to Datadog
        """
        # Initialize Vertex AI
        project_id = os.getenv('PROJECT_ID', 'v-commerce-480915')
        location = os.getenv('LOCATION', 'us-central1')
        
        try:
            vertexai.init(project=project_id, location=location)
            self.model = GenerativeModel("gemini-2.0-flash")
            logger.info(f"Gemini model initialized (project: {project_id}, location: {location})")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            self.model = None
        
        # Initialize clients
        self.dd_client = datadog_client or DatadogClient()
        self.alert_sender = alert_sender or AlertSender()
        
        # Configuration
        self.error_prediction_threshold = float(os.getenv('ERROR_PREDICTION_THRESHOLD', '0.02'))
        self.latency_threshold = float(os.getenv('LATENCY_THRESHOLD', '3.0'))
        
        logger.info("InsightsGenerator initialized")

    def _call_gemini(self, prompt: str) -> Optional[str]:
        """Make a call to Gemini and return the response text"""
        if not self.model:
            logger.error("Gemini model not initialized")
            return None
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            return None

    def _parse_json_response(self, response_text: str) -> Optional[Dict]:
        """Extract and parse JSON from Gemini response"""
        if not response_text:
            return None
        
        try:
            # Try to find JSON in the response (may be wrapped in markdown code blocks)
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            
            # Try to find raw JSON object
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                return json.loads(json_match.group(0))
            
            # Last resort: try to parse the whole response
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON from Gemini response: {e}")
            return None

    def predict_errors(self, force_analysis: bool = False) -> Dict[str, Any]:
        """
        Predict potential errors using hybrid approach.
        
        Step 1: Quick rule-based check (FREE)
        Step 2: If concerning, use Gemini for deep analysis (COSTS TOKENS)
        
        Args:
            force_analysis: If True, skip rule-based check and go straight to Gemini
            
        Returns:
            Dict with prediction results
        """
        logger.info("Starting error prediction...")
        
        # LEVEL 1: Quick health check (FREE - no LLM call)
        if not force_analysis:
            quick_check = self.dd_client.get_quick_health_check()
            
            if not quick_check["needs_deep_analysis"]:
                logger.info("Quick check passed - no deep analysis needed")
                result = {
                    "probability": 0.1,
                    "status": "healthy",
                    "analysis_type": "rule_based",
                    "message": "All metrics within normal thresholds",
                    "concerns": []
                }
                
                # Still emit the metric
                self.alert_sender.emit_metric(
                    "llm.prediction.error_probability",
                    result["probability"],
                    tags=["analysis_type:rule_based"]
                )
                
                self.alert_sender.send_insights_generated_event("error_prediction", True)
                return result
            
            logger.info(f"Concerns detected: {quick_check['concerns']} - running deep analysis")
        
        # LEVEL 2: Gemini deep analysis (COSTS TOKENS)
        try:
            # Fetch detailed metrics
            error_metrics = self.dd_client.get_error_metrics(time_window_hours=1)
            llm_metrics = self.dd_client.get_llm_metrics(time_window_hours=24)
            
            # Build context for Gemini
            metrics_context = self._format_metrics_for_prompt(error_metrics, llm_metrics)
            
            prompt = f"""You are an expert SRE analyzing observability data for an e-commerce platform called V-Commerce.

## Platform Architecture
The platform has the following LLM-powered services:
1. **chatbotservice** - Main customer chat interface, handles product queries and recommendations
2. **shoppingassistantservice** - AI shopping assistant for personalized recommendations  
3. **peau_agent** (PEAU Agent) - Proactive Engagement and Upsell agent, sends proactive messages

All services use Gemini LLM via Vertex AI and share the same project quotas.

## Current Telemetry Data (Last 1 Hour)
{metrics_context}

## Your Task
Analyze these metrics and predict SPECIFIC failures that may occur in the next 2 hours.

**IMPORTANT**: For each service showing concerning metrics, provide:
- What specifically will fail
- When it will likely happen
- What users will experience
- How to prevent it

## Response Format (JSON)
Respond with valid JSON only:
{{
    "probability": <float 0-1, overall probability of service degradation>,
    "confidence": <float 0-1, your confidence in this prediction>,
    "status": "<healthy|warning|critical>",
    "failure_predictions": [
        {{
            "service": "<exact service name>",
            "failure_mode": "<what will fail: e.g., 'Request timeouts', 'Rate limit errors', 'Quality degradation'>",
            "probability": <float 0-1, probability for this specific service>,
            "time_to_failure_minutes": <estimated minutes until failure>,
            "user_impact": "<what users will experience>",
            "symptoms": ["<observable symptom 1>", "<symptom 2>"],
            "root_cause": "<technical root cause>",
            "mitigation": "<specific action to prevent>"
        }}
    ],
    "affected_services": ["<list of all services that may be affected>"],
    "time_to_issue_hours": <overall estimated hours until first failure>,
    "recommended_actions": [
        "<specific action 1 with service name>",
        "<specific action 2 with service name>"
    ],
    "prediction_markdown": "<Complete markdown-formatted analysis - see format below>"
}}

## prediction_markdown Format
The prediction_markdown field MUST contain a complete markdown analysis like this:

```
## 🔮 AI Failure Prediction Report

### Overall Assessment
**Status**: <STATUS>
**Probability of Service Degradation**: <XX%>
**Estimated Time to First Failure**: <X hours/minutes>

### ⚠️ Services at Risk

#### 1. [SERVICE_NAME]
- **Risk Level**: <High/Medium/Low> (<XX%> probability)
- **Predicted Failure**: <failure mode>
- **Time to Failure**: ~<X> minutes
- **User Impact**: <what users will see>
- **Root Cause**: <technical cause>
- **Mitigation**: <specific fix>

#### 2. [NEXT_SERVICE_NAME]
...

### 📋 Recommended Actions
1. **[Priority 1]**: <action with service name>
2. **[Priority 2]**: <action with service name>

### 📊 Supporting Metrics
- <metric 1>: <value> (<interpretation>)
- <metric 2>: <value> (<interpretation>)
```

Be specific, actionable, and focus on preventing failures before they occur."""

            response = self._call_gemini(prompt)
            result = self._parse_json_response(response)
            
            if result:
                result["analysis_type"] = "gemini_deep"
                
                # Build full AI analysis text for monitor display
                full_analysis = self._build_full_analysis_text(result)
                
                # Extract root cause from failure predictions if available
                failure_preds = result.get("failure_predictions", [])
                if failure_preds:
                    # Sort by probability and get the highest risk prediction
                    sorted_preds = sorted(failure_preds, key=lambda x: x.get("probability", 0), reverse=True)
                    top_pred = sorted_preds[0]
                    
                    # Build a detailed cause string
                    cause = f"{top_pred.get('service', 'Unknown')}: {top_pred.get('failure_mode', 'Unknown failure')} - {top_pred.get('root_cause', 'Unknown cause')}"
                else:
                    cause = result.get("cause", "Unknown")
                
                # Send alerts based on results
                self.alert_sender.send_error_prediction(
                    probability=result.get("probability", 0),
                    cause=cause,
                    recommended_actions=result.get("recommended_actions", []),
                    affected_services=result.get("affected_services", []),
                    time_to_issue_hours=result.get("time_to_issue_hours") or 2.0,
                    full_ai_analysis=full_analysis
                )
                
                self.alert_sender.send_insights_generated_event("error_prediction", True)
                logger.info(f"Error prediction complete: {result.get('probability', 0):.2%} probability")
                return result
            else:
                logger.error("Failed to parse Gemini response for error prediction")
                return {"probability": 0, "status": "unknown", "error": "Failed to parse response"}
                
        except Exception as e:
            logger.error(f"Error prediction failed: {e}")
            self.alert_sender.send_insights_generated_event("error_prediction", False)
            return {"probability": 0, "status": "error", "error": str(e)}

    def suggest_cost_savings(self) -> Dict[str, Any]:
        """
        Analyze token usage and suggest cost optimization strategies.
        
        Returns:
            Dict with cost analysis and recommendations
        """
        logger.info("Starting cost optimization analysis...")
        
        try:
            # Get token usage by service
            token_usage = self.dd_client.get_token_usage_by_service(time_window_hours=24)
            
            # Calculate totals
            total_cost = sum(s.get("cost_usd_estimated", 0) for s in token_usage.values())
            total_tokens = sum(s.get("total_tokens", 0) for s in token_usage.values())
            
            # Build context for Gemini
            usage_context = self._format_token_usage_for_prompt(token_usage)
            
            prompt = f"""You are a cloud cost optimization expert analyzing LLM token usage for an e-commerce platform.

Here is the token usage data for the last 24 hours:

{usage_context}

**Total Daily Cost:** ${total_cost:.2f}
**Total Tokens:** {total_tokens:,}

Analyze this usage and provide cost optimization recommendations.

Respond in JSON format:
{{
    "daily_cost": <current daily cost>,
    "monthly_projected": <projected monthly cost>,
    "potential_savings_monthly": <potential monthly savings in USD>,
    "savings_percentage": <potential savings as percentage>,
    "analysis": "<brief analysis of spending patterns>",
    "recommendations": [
        {{
            "title": "<short title>",
            "description": "<detailed description of the optimization>",
            "estimated_savings": <monthly savings in USD>,
            "effort": "<low|medium|high>",
            "priority": <1-5, 1 being highest priority>
        }}
    ]
}}

Focus on practical optimizations like:
- Response caching
- Prompt optimization (reducing token count)
- Model tiering (using cheaper models for simple tasks)
- Request batching
- Eliminating redundant queries"""

            response = self._call_gemini(prompt)
            result = self._parse_json_response(response)
            
            if result:
                # Send report to Datadog
                self.alert_sender.send_cost_optimization_report(
                    current_daily_cost=result.get("daily_cost", total_cost),
                    projected_monthly_cost=result.get("monthly_projected", total_cost * 30),
                    potential_savings=result.get("potential_savings_monthly", 0),
                    recommendations=result.get("recommendations", [])
                )
                
                self.alert_sender.send_insights_generated_event("cost_optimization", True)
                logger.info(f"Cost analysis complete: ${total_cost:.2f}/day, potential savings: ${result.get('potential_savings_monthly', 0):.2f}/month")
                return result
            else:
                logger.error("Failed to parse Gemini response for cost analysis")
                return {"error": "Failed to parse response"}
                
        except Exception as e:
            logger.error(f"Cost optimization analysis failed: {e}")
            self.alert_sender.send_insights_generated_event("cost_optimization", False)
            return {"error": str(e)}

    def generate_health_summary(self) -> Dict[str, Any]:
        """
        Generate a natural language health summary of the system.
        
        Returns:
            Dict with health summary
        """
        logger.info("Generating health summary...")
        
        try:
            # Get quick metrics
            quick_check = self.dd_client.get_quick_health_check()
            llm_metrics = self.dd_client.get_llm_metrics(time_window_hours=1)
            
            # Build context
            metrics_context = f"""
Quick Health Check:
- Error Rate: {quick_check['metrics'].get('error_rate', 'N/A')}
- Latency: {quick_check['metrics'].get('latency_avg', 'N/A')}s
- Hallucination Rate: {quick_check['metrics'].get('hallucination_rate', 'N/A')}
- Concerns: {', '.join(quick_check['concerns']) if quick_check['concerns'] else 'None'}

Last Hour LLM Metrics:
- Request Duration Avg: {llm_metrics.get('request_duration', {}).get('avg', 'N/A')}s
- Quality Score Avg: {llm_metrics.get('quality_score', {}).get('avg', 'N/A')}
"""

            prompt = f"""You are a senior SRE creating a status update for an e-commerce platform with LLM-powered services.

Current Metrics:
{metrics_context}

Generate a brief, executive-friendly health summary.

Respond in JSON format:
{{
    "overall_status": "<healthy|warning|critical>",
    "summary": "<2-3 sentence executive summary>",
    "highlights": ["<list of positive highlights, max 3>"],
    "concerns": ["<list of concerns if any, max 3>"],
    "recommendations": ["<list of recommended actions if any, max 3>"]
}}

Keep it concise and actionable. Focus on business impact."""

            response = self._call_gemini(prompt)
            result = self._parse_json_response(response)
            
            if result:
                # Send to Datadog
                self.alert_sender.send_health_summary(
                    overall_status=result.get("overall_status", "unknown"),
                    summary_text=result.get("summary", ""),
                    highlights=result.get("highlights", []),
                    concerns=result.get("concerns", []),
                    recommendations=result.get("recommendations", [])
                )
                
                self.alert_sender.send_insights_generated_event("health_summary", True)
                logger.info(f"Health summary generated: {result.get('overall_status', 'unknown')}")
                return result
            else:
                logger.error("Failed to parse Gemini response for health summary")
                return {"error": "Failed to parse response"}
                
        except Exception as e:
            logger.error(f"Health summary generation failed: {e}")
            self.alert_sender.send_insights_generated_event("health_summary", False)
            return {"error": str(e)}

    def run_all_analyses(self) -> Dict[str, Any]:
        """Run all analyses and return combined results"""
        logger.info("Running all analyses...")
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "error_prediction": self.predict_errors(force_analysis=True),
            "cost_optimization": self.suggest_cost_savings(),
            "health_summary": self.generate_health_summary()
        }
        
        logger.info("All analyses complete")
        return results

    def _format_metrics_for_prompt(self, error_metrics: Dict, llm_metrics: Dict) -> str:
        """Format metrics for inclusion in Gemini prompt"""
        lines = []
        
        lines.append("**Error Metrics (Last Hour):**")
        for name, data in error_metrics.items():
            if isinstance(data, dict):
                lines.append(f"- {name}: latest={data.get('latest', 'N/A')}, trend={data.get('trend', 'N/A')}, avg={data.get('avg', 'N/A')}")
        
        lines.append("\n**LLM Metrics (Last 24 Hours):**")
        for name, data in llm_metrics.items():
            if isinstance(data, dict):
                lines.append(f"- {name}: latest={data.get('latest', 'N/A')}, avg={data.get('avg', 'N/A')}")
        
        return "\n".join(lines)

    def _format_token_usage_for_prompt(self, token_usage: Dict) -> str:
        """Format token usage for inclusion in Gemini prompt"""
        lines = ["| Service | Input Tokens | Output Tokens | Total Tokens | Est. Cost |"]
        lines.append("|---------|--------------|---------------|--------------|-----------|")
        
        for service, data in token_usage.items():
            input_t = data.get("input_tokens", 0)
            output_t = data.get("output_tokens", 0)
            total_t = data.get("total_tokens", 0)
            cost = data.get("cost_usd_estimated", 0)
            lines.append(f"| {service} | {input_t:,} | {output_t:,} | {total_t:,} | ${cost:.4f} |")
        
        return "\n".join(lines)

    def _build_full_analysis_text(self, result: Dict) -> str:
        """
        Build a formatted markdown text of the full Gemini analysis.
        
        This is used to attach the AI analysis to Datadog metrics and events,
        allowing the monitor message to display detailed failure predictions.
        
        Args:
            result: The parsed Gemini analysis result
            
        Returns:
            Formatted markdown string with the full analysis
        """
        # If Gemini provided a pre-formatted markdown, use it
        if result.get("prediction_markdown"):
            return result["prediction_markdown"]
        
        # Otherwise, build markdown from structured data
        probability = result.get("probability", 0)
        confidence = result.get("confidence", 0)
        status = result.get("status", "unknown")
        affected_services = result.get("affected_services", [])
        time_to_issue = result.get("time_to_issue_hours")
        recommended_actions = result.get("recommended_actions", [])
        failure_predictions = result.get("failure_predictions", [])
        
        # Build the analysis text
        lines = [
            "## 🔮 AI Failure Prediction Report",
            "",
            "### Overall Assessment",
            f"**Status:** {status.upper()}",
            f"**Probability of Service Degradation:** {probability:.1%}",
        ]
        
        if confidence:
            lines.append(f"**Analysis Confidence:** {confidence:.1%}")
        
        if time_to_issue:
            if time_to_issue < 1:
                lines.append(f"**Estimated Time to First Failure:** ~{int(time_to_issue * 60)} minutes")
            else:
                lines.append(f"**Estimated Time to First Failure:** {time_to_issue:.1f} hours")
        
        # Add service-specific failure predictions if available
        if failure_predictions:
            lines.append("")
            lines.append("### ⚠️ Services at Risk")
            lines.append("")
            
            for i, pred in enumerate(failure_predictions, 1):
                service = pred.get("service", "Unknown Service")
                failure_mode = pred.get("failure_mode", "Unknown failure")
                svc_probability = pred.get("probability", 0)
                time_to_failure = pred.get("time_to_failure_minutes", 0)
                user_impact = pred.get("user_impact", "Unknown impact")
                root_cause = pred.get("root_cause", "Unknown cause")
                mitigation = pred.get("mitigation", "No mitigation specified")
                symptoms = pred.get("symptoms", [])
                
                # Determine risk level
                if svc_probability >= 0.8:
                    risk_level = "🔴 High"
                elif svc_probability >= 0.5:
                    risk_level = "🟡 Medium"
                else:
                    risk_level = "🟢 Low"
                
                lines.append(f"#### {i}. {service}")
                lines.append(f"- **Risk Level:** {risk_level} ({svc_probability:.0%} probability)")
                lines.append(f"- **Predicted Failure:** {failure_mode}")
                lines.append(f"- **Time to Failure:** ~{time_to_failure} minutes")
                lines.append(f"- **User Impact:** {user_impact}")
                
                if symptoms:
                    lines.append(f"- **Symptoms:** {', '.join(symptoms)}")
                
                lines.append(f"- **Root Cause:** {root_cause}")
                lines.append(f"- **Mitigation:** {mitigation}")
                lines.append("")
        
        elif affected_services:
            # Fallback to basic affected services list
            lines.append("")
            lines.append("### Affected Services")
            services_str = ", ".join(affected_services)
            lines.append(f"**Services at Risk:** {services_str}")
            
            # Include legacy 'cause' field if present
            cause = result.get("cause", "")
            if cause and cause != "System operating normally":
                lines.append("")
                lines.append("### Root Cause Analysis")
                lines.append(cause)
        
        # Add recommended actions
        if recommended_actions:
            lines.append("")
            lines.append("### 📋 Recommended Actions")
            for i, action in enumerate(recommended_actions, 1):
                lines.append(f"{i}. {action}")
        
        lines.append("")
        lines.append("---")
        lines.append("*Generated by V-Commerce Observability Insights Service (Gemini AI)*")
        
        return "\n".join(lines)

