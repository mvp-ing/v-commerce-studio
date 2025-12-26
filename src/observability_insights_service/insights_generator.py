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
            
            prompt = f"""You are an expert SRE analyzing observability data for an e-commerce platform with LLM-powered services (chatbot, shopping assistant, and a proactive engagement agent).

Here is the current telemetry data:

{metrics_context}

Based on these metrics and trends, analyze the system health and predict potential issues.

Respond in JSON format:
{{
    "probability": <float 0-1, probability of service degradation in next 2 hours>,
    "confidence": <float 0-1, your confidence in this prediction>,
    "status": "<healthy|warning|critical>",
    "cause": "<root cause analysis if probability > 0.5, otherwise 'System operating normally'>",
    "affected_services": ["<list of services likely to be affected>"],
    "time_to_issue_hours": <estimated hours until issue occurs, or null if healthy>,
    "recommended_actions": ["<list of 2-4 specific actions to prevent issues>"]
}}

Be specific and actionable. Focus on LLM-specific concerns like rate limits, token quotas, model latency, and quality degradation."""

            response = self._call_gemini(prompt)
            result = self._parse_json_response(response)
            
            if result:
                result["analysis_type"] = "gemini_deep"
                
                # Send alerts based on results
                self.alert_sender.send_error_prediction(
                    probability=result.get("probability", 0),
                    cause=result.get("cause", "Unknown"),
                    recommended_actions=result.get("recommended_actions", []),
                    affected_services=result.get("affected_services", []),
                    time_to_issue_hours=result.get("time_to_issue_hours", 2.0)
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
