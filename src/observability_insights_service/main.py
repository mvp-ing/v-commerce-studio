#!/usr/bin/env python
"""
Observability Insights Service - Main Application (Agent-Based)

This service provides AI-powered observability insights using an ADK-based agent.
The agent has access to tools for:
- Querying Datadog metrics
- Performing health checks
- Analyzing token usage and costs
- Sending alerts and custom metrics

The agent autonomously decides which tools to use based on the task.
"""

import os
import logging
import atexit
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler

# ============================================
# Datadog APM Setup
# ============================================
from ddtrace import tracer, patch_all, config

config.service = "observability-insights-service"
config.flask["service_name"] = "observability-insights-service"
patch_all()

# ============================================

from observability_agent import ObservabilityAgent
from datadog_client import DatadogClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "severity": "%(levelname)s", "service": "observability-insights-service", "message": "%(message)s", "dd.trace_id": "%(dd.trace_id)s", "dd.span_id": "%(dd.span_id)s"}',
    datefmt='%Y-%m-%dT%H:%M:%S.%fZ'
)
logger = logging.getLogger(__name__)

# ============================================
# Configuration
# ============================================
ERROR_PREDICTION_INTERVAL = int(os.getenv('ERROR_PREDICTION_INTERVAL_MINUTES', '5'))
COST_ANALYSIS_INTERVAL = int(os.getenv('COST_ANALYSIS_INTERVAL_HOURS', '1'))
HEALTH_SUMMARY_INTERVAL = int(os.getenv('HEALTH_SUMMARY_INTERVAL_MINUTES', '15'))
HTTP_PORT = int(os.getenv('HTTP_PORT', '8080'))

# ============================================
# Initialize Components
# ============================================
dd_client = DatadogClient()
agent = None  # Initialized lazily to avoid startup issues

def get_agent():
    """Lazy initialization of the agent"""
    global agent
    if agent is None:
        agent = ObservabilityAgent()
    return agent

# ============================================
# Flask Application
# ============================================
app = Flask(__name__)
CORS(app)

# ============================================
# Scheduled Jobs (Hybrid Approach)
# ============================================
scheduler = BackgroundScheduler()


def scheduled_error_prediction():
    """Scheduled: Run error prediction with hybrid approach"""
    logger.info("⏰ Scheduled: Running error prediction...")
    try:
        # Level 1: Quick rule-based check (FREE)
        quick_check = dd_client.get_quick_health_check()
        
        if not quick_check.get("needs_deep_analysis"):
            logger.info("Quick check passed - system healthy, skipping AI analysis")
            return
        
        # Level 2: AI agent analysis (uses tokens)
        logger.info(f"Concerns detected: {quick_check.get('concerns')} - running AI analysis")
        result = get_agent().predict_errors()
        logger.info(f"AI prediction complete: {len(result.get('tool_calls', []))} tool calls")
    except Exception as e:
        logger.error(f"Scheduled error prediction failed: {e}")


def scheduled_cost_analysis():
    """Scheduled: Run cost optimization analysis"""
    logger.info("⏰ Scheduled: Running cost analysis...")
    try:
        result = get_agent().analyze_costs()
        logger.info(f"Cost analysis complete")
    except Exception as e:
        logger.error(f"Scheduled cost analysis failed: {e}")


def scheduled_health_summary():
    """Scheduled: Generate health summary"""
    logger.info("⏰ Scheduled: Generating health summary...")
    try:
        result = get_agent().generate_health_summary()
        logger.info(f"Health summary complete")
    except Exception as e:
        logger.error(f"Scheduled health summary failed: {e}")


# Add scheduled jobs
scheduler.add_job(
    func=scheduled_error_prediction,
    trigger='interval',
    minutes=ERROR_PREDICTION_INTERVAL,
    id='error_prediction',
    name='Error Prediction',
    replace_existing=True
)

scheduler.add_job(
    func=scheduled_cost_analysis,
    trigger='interval',
    hours=COST_ANALYSIS_INTERVAL,
    id='cost_analysis',
    name='Cost Analysis',
    replace_existing=True
)

scheduler.add_job(
    func=scheduled_health_summary,
    trigger='interval',
    minutes=HEALTH_SUMMARY_INTERVAL,
    id='health_summary',
    name='Health Summary',
    replace_existing=True
)

# ============================================
# REST API Endpoints
# ============================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check for K8s probes"""
    return jsonify({
        'status': 'healthy',
        'service': 'observability-insights-service',
        'mode': 'agent-based',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/ready', methods=['GET'])
def readiness_check():
    """Readiness check"""
    dd_connected = dd_client.validate_connection()
    return jsonify({
        'ready': dd_connected,
        'datadog_connected': dd_connected,
        'timestamp': datetime.now().isoformat()
    }), 200 if dd_connected else 503


@app.route('/insights/quick-check', methods=['GET'])
def quick_health_check():
    """Quick rule-based health check (FREE - no LLM tokens)"""
    result = dd_client.get_quick_health_check()
    return jsonify({
        'success': True,
        'timestamp': datetime.now().isoformat(),
        'result': result,
        'note': 'This check uses no LLM tokens'
    })


@app.route('/insights/errors', methods=['GET'])
def get_error_prediction():
    """Run AI agent to predict errors"""
    force = request.args.get('force', 'false').lower() == 'true'
    
    # Check if we should skip AI analysis
    if not force:
        quick_check = dd_client.get_quick_health_check()
        if not quick_check.get("needs_deep_analysis"):
            return jsonify({
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'analysis_type': 'rule_based',
                'result': {
                    'status': 'healthy',
                    'message': 'Quick check passed - no concerns detected',
                    'probability': 0.1
                },
                'note': 'AI analysis skipped - no concerns detected'
            })
    
    logger.info(f"Running AI error prediction (force={force})")
    result = get_agent().predict_errors()
    
    return jsonify({
        'success': True,
        'timestamp': datetime.now().isoformat(),
        'analysis_type': 'agent_based',
        'result': result
    })


@app.route('/insights/costs', methods=['GET'])
def get_cost_optimization():
    """Run AI agent to analyze costs"""
    result = get_agent().analyze_costs()
    return jsonify({
        'success': True,
        'timestamp': datetime.now().isoformat(),
        'result': result
    })


@app.route('/insights/health', methods=['GET'])
def get_health_summary():
    """Run AI agent to generate health summary"""
    result = get_agent().generate_health_summary()
    return jsonify({
        'success': True,
        'timestamp': datetime.now().isoformat(),
        'result': result
    })


@app.route('/agent/chat', methods=['POST'])
def agent_chat():
    """
    Chat with the observability agent using natural language.
    
    Send any task and the agent will use its tools to complete it.
    
    Example tasks:
    - "Check if there are any issues with the chatbot service"
    - "How much are we spending on LLM tokens?"
    - "Is the system healthy? Give me a quick overview"
    - "Predict if we'll have any issues in the next 2 hours"
    """
    data = request.get_json() or {}
    task = data.get('task') or data.get('message') or data.get('prompt')
    
    if not task:
        return jsonify({
            'success': False,
            'error': 'Please provide a task/message in the request body'
        }), 400
    
    user_id = data.get('user_id', 'api_user')
    
    logger.info(f"Agent chat request: {task[:100]}...")
    result = get_agent().analyze_sync(task, user_id)
    
    return jsonify({
        'success': True,
        'timestamp': datetime.now().isoformat(),
        'result': result
    })


@app.route('/agent/tools', methods=['GET'])
def list_tools():
    """List available tools the agent can use"""
    tools = [
        {
            "name": "query_datadog_metrics",
            "description": "Query time-series metrics from Datadog",
            "parameters": ["metric_name", "service", "time_window_hours", "aggregation"]
        },
        {
            "name": "get_quick_health_check",
            "description": "Quick rule-based health check (FREE)",
            "parameters": []
        },
        {
            "name": "get_llm_token_usage",
            "description": "Get token usage breakdown by service",
            "parameters": ["time_window_hours"]
        },
        {
            "name": "get_error_metrics",
            "description": "Get error rates and trends",
            "parameters": ["time_window_hours"]
        },
        {
            "name": "get_full_llm_metrics",
            "description": "Get comprehensive LLM metrics",
            "parameters": ["service", "time_window_hours"]
        },
        {
            "name": "send_datadog_event",
            "description": "Send an event to Datadog",
            "parameters": ["title", "text", "alert_type", "tags"]
        },
        {
            "name": "emit_datadog_metric",
            "description": "Emit a custom metric to Datadog",
            "parameters": ["metric_name", "value", "tags"]
        }
    ]
    return jsonify({
        'tools': tools,
        'count': len(tools)
    })


@app.route('/config', methods=['GET'])
def get_config():
    """Return service configuration"""
    return jsonify({
        'mode': 'agent-based',
        'error_prediction_interval_minutes': ERROR_PREDICTION_INTERVAL,
        'cost_analysis_interval_hours': COST_ANALYSIS_INTERVAL,
        'health_summary_interval_minutes': HEALTH_SUMMARY_INTERVAL,
        'dd_site': os.getenv('DD_SITE', 'not_set'),
        'dd_env': os.getenv('DD_ENV', 'not_set'),
        'project_id': os.getenv('PROJECT_ID', 'not_set'),
        'scheduler_running': scheduler.running
    })


@app.route('/scheduler/jobs', methods=['GET'])
def get_scheduler_jobs():
    """Get scheduler status"""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run': job.next_run_time.isoformat() if job.next_run_time else None
        })
    return jsonify({'scheduler_running': scheduler.running, 'jobs': jobs})


@app.route('/scheduler/trigger/<job_id>', methods=['POST'])
def trigger_job(job_id: str):
    """Manually trigger a scheduled job"""
    job = scheduler.get_job(job_id)
    if not job:
        return jsonify({'error': f'Job {job_id} not found'}), 404
    job.modify(next_run_time=datetime.now())
    return jsonify({'success': True, 'message': f'Job {job_id} triggered'})


# ============================================
# Main
# ============================================

def main():
    logger.info("=" * 60)
    logger.info("🚀 Starting Observability Insights Service (Agent Mode)")
    logger.info("=" * 60)
    logger.info(f"Configuration:")
    logger.info(f"  - Mode: Agent-based (ADK)")
    logger.info(f"  - Error Prediction: every {ERROR_PREDICTION_INTERVAL} min")
    logger.info(f"  - Cost Analysis: every {COST_ANALYSIS_INTERVAL} hour(s)")
    logger.info(f"  - Health Summary: every {HEALTH_SUMMARY_INTERVAL} min")
    logger.info(f"  - HTTP Port: {HTTP_PORT}")
    logger.info("=" * 60)
    
    # Validate Datadog
    if dd_client.validate_connection():
        logger.info("✅ Datadog API connected")
    else:
        logger.warning("⚠️ Datadog API connection failed")
    
    # Start scheduler
    scheduler.start()
    logger.info("✅ Scheduler started")
    
    atexit.register(lambda: scheduler.shutdown())
    
    # Start Flask
    logger.info(f"🌐 Starting HTTP server on port {HTTP_PORT}")
    app.run(host='0.0.0.0', port=HTTP_PORT, debug=False)


if __name__ == '__main__':
    main()
