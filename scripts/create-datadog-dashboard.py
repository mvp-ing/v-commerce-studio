#!/usr/bin/env python3
"""
Datadog Dashboard Creator

This script creates the V-Commerce LLM Observability Dashboard using the Datadog API.
The dashboard provides comprehensive visibility into the LLM-powered e-commerce application.

Dashboard Sections:
1. Application Health Overview - RED metrics, service status
2. LLM Observability Panel - token usage, costs, latency
3. AI Insights Panel - predictions from Observability Insights Service
4. Detection Rules Status - monitor widgets for all 5 detection rules

Usage:
    source .env.datadog
    python3 scripts/create-datadog-dashboard.py

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


def get_llm_observability_dashboard() -> Dict[str, Any]:
    """Return the comprehensive LLM Observability Dashboard configuration."""
    return {
        "title": "V-Commerce LLM Observability Dashboard",
        "description": "Comprehensive observability for V-Commerce AI-powered e-commerce platform. Includes LLM metrics, detection rules status, and AI-powered insights.",
        "layout_type": "ordered",
        "tags": [
            "team:llm"
        ],
        "widgets": get_dashboard_widgets()
    }


def get_dashboard_widgets() -> List[Dict[str, Any]]:
    """Return all dashboard widgets in ordered layout."""
    widgets = []
    
    # ============================================
    # SECTION 1: Application Health Overview
    # ============================================
    widgets.append({
        "definition": {
            "title": "🏥 Application Health Overview",
            "title_align": "left",
            "type": "group",
            "background_color": "blue",
            "layout_type": "ordered",
            "widgets": [
                # Row 1: Key Metrics
                {
                    "definition": {
                        "title": "Request Rate",
                        "title_size": "16",
                        "title_align": "left",
                        "type": "query_value",
                        "requests": [
                            {
                                "response_format": "scalar",
                                "queries": [
                                    {
                                        "data_source": "metrics",
                                        "name": "query1",
                                        "query": "sum:trace.http.request.hits{*}.as_rate()",
                                        "aggregator": "avg"
                                    }
                                ],
                                "formulas": [{"formula": "query1"}]
                            }
                        ],
                        "autoscale": True,
                        "precision": 1,
                        "timeseries_background": {"type": "area"}
                    },
                    "layout": {"x": 0, "y": 0, "width": 3, "height": 2}
                },
                {
                    "definition": {
                        "title": "Error Rate",
                        "title_size": "16",
                        "title_align": "left",
                        "type": "query_value",
                        "requests": [
                            {
                                "response_format": "scalar",
                                "queries": [
                                    {
                                        "data_source": "metrics",
                                        "name": "query1",
                                        "query": "sum:trace.http.request.errors{*}.as_rate()",
                                        "aggregator": "avg"
                                    }
                                ],
                                "formulas": [{"formula": "query1"}],
                                "conditional_formats": [
                                    {"comparator": ">", "value": 1, "palette": "white_on_red"},
                                    {"comparator": ">", "value": 0, "palette": "white_on_yellow"},
                                    {"comparator": "<=", "value": 0, "palette": "white_on_green"}
                                ]
                            }
                        ],
                        "autoscale": True,
                        "precision": 1,
                        "timeseries_background": {"type": "area"}
                    },
                    "layout": {"x": 3, "y": 0, "width": 3, "height": 2}
                },
                {
                    "definition": {
                        "title": "Avg Latency (ms)",
                        "title_size": "16",
                        "title_align": "left",
                        "type": "query_value",
                        "requests": [
                            {
                                "response_format": "scalar",
                                "queries": [
                                    {
                                        "data_source": "metrics",
                                        "name": "query1",
                                        "query": "avg:trace.http.request.duration{*}",
                                        "aggregator": "avg"
                                    }
                                ],
                                "formulas": [{"formula": "query1 * 1000"}]
                            }
                        ],
                        "autoscale": True,
                        "precision": 0,
                        "custom_unit": "ms",
                        "timeseries_background": {"type": "area"}
                    },
                    "layout": {"x": 6, "y": 0, "width": 3, "height": 2}
                },
                {
                    "definition": {
                        "title": "Active Services",
                        "title_size": "16",
                        "title_align": "left",
                        "type": "query_value",
                        "requests": [
                            {
                                "response_format": "scalar",
                                "queries": [
                                    {
                                        "data_source": "metrics",
                                        "name": "query1",
                                        "query": "count_not_null(sum:trace.http.request.hits{*} by {service})",
                                        "aggregator": "last"
                                    }
                                ],
                                "formulas": [{"formula": "query1"}]
                            }
                        ],
                        "autoscale": True,
                        "precision": 0
                    },
                    "layout": {"x": 9, "y": 0, "width": 3, "height": 2}
                },
                # Row 2: Timeseries charts
                {
                    "definition": {
                        "title": "Request Rate by Service",
                        "title_size": "16",
                        "title_align": "left",
                        "show_legend": True,
                        "legend_layout": "auto",
                        "legend_columns": ["avg", "min", "max", "value", "sum"],
                        "type": "timeseries",
                        "requests": [
                            {
                                "formulas": [{"formula": "query1"}],
                                "queries": [
                                    {
                                        "data_source": "metrics",
                                        "name": "query1",
                                        "query": "sum:trace.http.request.hits{*} by {service}.as_rate()"
                                    }
                                ],
                                "response_format": "timeseries",
                                "style": {"palette": "dog_classic", "line_type": "solid", "line_width": "normal"},
                                "display_type": "line"
                            }
                        ]
                    },
                    "layout": {"x": 0, "y": 2, "width": 6, "height": 3}
                },
                {
                    "definition": {
                        "title": "P95 Latency by Service",
                        "title_size": "16",
                        "title_align": "left",
                        "show_legend": True,
                        "legend_layout": "auto",
                        "legend_columns": ["avg", "min", "max", "value"],
                        "type": "timeseries",
                        "requests": [
                            {
                                "formulas": [{"formula": "query1"}],
                                "queries": [
                                    {
                                        "data_source": "metrics",
                                        "name": "query1",
                                        "query": "p95:trace.http.request.duration{*} by {service}"
                                    }
                                ],
                                "response_format": "timeseries",
                                "style": {"palette": "cool", "line_type": "solid", "line_width": "normal"},
                                "display_type": "line"
                            }
                        ]
                    },
                    "layout": {"x": 6, "y": 2, "width": 6, "height": 3}
                },
                # Row 3: Error details
                {
                    "definition": {
                        "title": "Errors by Service",
                        "title_size": "16",
                        "title_align": "left",
                        "show_legend": True,
                        "legend_layout": "auto",
                        "type": "timeseries",
                        "requests": [
                            {
                                "formulas": [{"formula": "query1"}],
                                "queries": [
                                    {
                                        "data_source": "metrics",
                                        "name": "query1",
                                        "query": "sum:trace.http.request.errors{*} by {service}.as_count()"
                                    }
                                ],
                                "response_format": "timeseries",
                                "style": {"palette": "warm", "line_type": "solid", "line_width": "normal"},
                                "display_type": "bars"
                            }
                        ]
                    },
                    "layout": {"x": 0, "y": 5, "width": 6, "height": 3}
                },
                {
                    "definition": {
                        "title": "Top Services by Request Count",
                        "title_size": "16",
                        "title_align": "left",
                        "type": "toplist",
                        "requests": [
                            {
                                "formulas": [{"formula": "query1", "limit": {"count": 10, "order": "desc"}}],
                                "queries": [
                                    {
                                        "data_source": "metrics",
                                        "name": "query1",
                                        "query": "sum:trace.http.request.hits{*} by {service}.as_count()",
                                        "aggregator": "sum"
                                    }
                                ],
                                "response_format": "scalar"
                            }
                        ]
                    },
                    "layout": {"x": 6, "y": 5, "width": 6, "height": 3}
                }
            ]
        },
        "layout": {"x": 0, "y": 0, "width": 12, "height": 9}
    })
    
    # ============================================
    # SECTION 2: LLM Observability Panel
    # ============================================
    widgets.append({
        "definition": {
            "title": "🤖 LLM Observability",
            "title_align": "left",
            "type": "group",
            "background_color": "purple",
            "layout_type": "ordered",
            "widgets": [
                # Key LLM Metrics Row
                {
                    "definition": {
                        "title": "Total Tokens (Input)",
                        "title_size": "16",
                        "title_align": "left",
                        "type": "query_value",
                        "requests": [
                            {
                                "response_format": "scalar",
                                "queries": [
                                    {
                                        "data_source": "metrics",
                                        "name": "query1",
                                        "query": "sum:llm.tokens.input{*}.as_count()",
                                        "aggregator": "sum"
                                    }
                                ],
                                "formulas": [{"formula": "query1"}]
                            }
                        ],
                        "autoscale": True,
                        "precision": 0,
                        "timeseries_background": {"type": "area"}
                    },
                    "layout": {"x": 0, "y": 0, "width": 2, "height": 2}
                },
                {
                    "definition": {
                        "title": "Total Tokens (Output)",
                        "title_size": "16",
                        "title_align": "left",
                        "type": "query_value",
                        "requests": [
                            {
                                "response_format": "scalar",
                                "queries": [
                                    {
                                        "data_source": "metrics",
                                        "name": "query1",
                                        "query": "sum:llm.tokens.output{*}.as_count()",
                                        "aggregator": "sum"
                                    }
                                ],
                                "formulas": [{"formula": "query1"}]
                            }
                        ],
                        "autoscale": True,
                        "precision": 0,
                        "timeseries_background": {"type": "area"}
                    },
                    "layout": {"x": 2, "y": 0, "width": 2, "height": 2}
                },
                {
                    "definition": {
                        "title": "Total Cost (USD)",
                        "title_size": "16",
                        "title_align": "left",
                        "type": "query_value",
                        "requests": [
                            {
                                "response_format": "scalar",
                                "queries": [
                                    {
                                        "data_source": "metrics",
                                        "name": "query1",
                                        "query": "sum:llm.tokens.total_cost_usd{*}",
                                        "aggregator": "sum"
                                    }
                                ],
                                "formulas": [{"formula": "query1"}]
                            }
                        ],
                        "precision": 4,
                        "custom_unit": "$",
                        "timeseries_background": {"type": "area"}
                    },
                    "layout": {"x": 4, "y": 0, "width": 2, "height": 2}
                },
                {
                    "definition": {
                        "title": "Cost Per Conversion",
                        "title_size": "16",
                        "title_align": "left",
                        "type": "query_value",
                        "requests": [
                            {
                                "response_format": "scalar",
                                "queries": [
                                    {
                                        "data_source": "metrics",
                                        "name": "query1",
                                        "query": "avg:llm.cost_per_conversion{*}",
                                        "aggregator": "avg"
                                    }
                                ],
                                "formulas": [{"formula": "query1"}]
                            }
                        ],
                        "precision": 4,
                        "custom_unit": "$",
                        "timeseries_background": {"type": "area"}
                    },
                    "layout": {"x": 6, "y": 0, "width": 2, "height": 2}
                },
                {
                    "definition": {
                        "title": "Quality Score",
                        "title_size": "16",
                        "title_align": "left",
                        "type": "query_value",
                        "requests": [
                            {
                                "response_format": "scalar",
                                "queries": [
                                    {
                                        "data_source": "metrics",
                                        "name": "query1",
                                        "query": "avg:llm.response.quality_score{*}",
                                        "aggregator": "avg"
                                    }
                                ],
                                "formulas": [{"formula": "query1"}],
                                "conditional_formats": [
                                    {"comparator": "<", "value": 0.6, "palette": "white_on_red"},
                                    {"comparator": "<", "value": 0.8, "palette": "white_on_yellow"},
                                    {"comparator": ">=", "value": 0.8, "palette": "white_on_green"}
                                ]
                            }
                        ],
                        "precision": 2,
                        "timeseries_background": {"type": "area"}
                    },
                    "layout": {"x": 8, "y": 0, "width": 2, "height": 2}
                },
                {
                    "definition": {
                        "title": "LLM Requests",
                        "title_size": "16",
                        "title_align": "left",
                        "type": "query_value",
                        "requests": [
                            {
                                "response_format": "scalar",
                                "queries": [
                                    {
                                        "data_source": "metrics",
                                        "name": "query1",
                                        "query": "sum:llm.request.count{*}.as_count()",
                                        "aggregator": "sum"
                                    }
                                ],
                                "formulas": [{"formula": "query1"}]
                            }
                        ],
                        "autoscale": True,
                        "precision": 0,
                        "timeseries_background": {"type": "area"}
                    },
                    "layout": {"x": 10, "y": 0, "width": 2, "height": 2}
                },
                # Token Usage Timeseries
                {
                    "definition": {
                        "title": "Token Usage Over Time",
                        "title_size": "16",
                        "title_align": "left",
                        "show_legend": True,
                        "legend_layout": "auto",
                        "legend_columns": ["avg", "sum", "value"],
                        "type": "timeseries",
                        "requests": [
                            {
                                "formulas": [
                                    {"formula": "query1", "alias": "Input Tokens"},
                                    {"formula": "query2", "alias": "Output Tokens"}
                                ],
                                "queries": [
                                    {
                                        "data_source": "metrics",
                                        "name": "query1",
                                        "query": "sum:llm.tokens.input{*}.as_count()"
                                    },
                                    {
                                        "data_source": "metrics",
                                        "name": "query2",
                                        "query": "sum:llm.tokens.output{*}.as_count()"
                                    }
                                ],
                                "response_format": "timeseries",
                                "style": {"palette": "dog_classic", "line_type": "solid", "line_width": "normal"},
                                "display_type": "area"
                            }
                        ]
                    },
                    "layout": {"x": 0, "y": 2, "width": 6, "height": 3}
                },
                {
                    "definition": {
                        "title": "LLM Cost Over Time (USD)",
                        "title_size": "16",
                        "title_align": "left",
                        "show_legend": True,
                        "legend_layout": "auto",
                        "type": "timeseries",
                        "requests": [
                            {
                                "formulas": [{"formula": "query1"}],
                                "queries": [
                                    {
                                        "data_source": "metrics",
                                        "name": "query1",
                                        "query": "sum:llm.tokens.total_cost_usd{*}"
                                    }
                                ],
                                "response_format": "timeseries",
                                "style": {"palette": "green", "line_type": "solid", "line_width": "thick"},
                                "display_type": "line"
                            }
                        ]
                    },
                    "layout": {"x": 6, "y": 2, "width": 6, "height": 3}
                },
                # LLM Request Duration
                {
                    "definition": {
                        "title": "LLM Request Duration by Service",
                        "title_size": "16",
                        "title_align": "left",
                        "show_legend": True,
                        "legend_layout": "auto",
                        "type": "timeseries",
                        "requests": [
                            {
                                "formulas": [{"formula": "query1"}],
                                "queries": [
                                    {
                                        "data_source": "metrics",
                                        "name": "query1",
                                        "query": "avg:llm.request.duration{*} by {service}"
                                    }
                                ],
                                "response_format": "timeseries",
                                "style": {"palette": "purple", "line_type": "solid", "line_width": "normal"},
                                "display_type": "line"
                            }
                        ]
                    },
                    "layout": {"x": 0, "y": 5, "width": 6, "height": 3}
                },
                {
                    "definition": {
                        "title": "Response Quality Score",
                        "title_size": "16",
                        "title_align": "left",
                        "show_legend": True,
                        "legend_layout": "auto",
                        "type": "timeseries",
                        "requests": [
                            {
                                "formulas": [{"formula": "query1"}],
                                "queries": [
                                    {
                                        "data_source": "metrics",
                                        "name": "query1",
                                        "query": "avg:llm.response.quality_score{*} by {service}"
                                    }
                                ],
                                "response_format": "timeseries",
                                "style": {"palette": "classic", "line_type": "solid", "line_width": "normal"},
                                "display_type": "line"
                            }
                        ],
                        "yaxis": {"min": "0", "max": "1"},
                        "markers": [
                            {"value": "y = 0.6", "display_type": "error dashed", "label": "Threshold"}
                        ]
                    },
                    "layout": {"x": 6, "y": 5, "width": 6, "height": 3}
                }
            ]
        },
        "layout": {"x": 0, "y": 9, "width": 12, "height": 9}
    })
    
    # ============================================
    # SECTION 3: Detection Rules Status
    # ============================================
    widgets.append({
        "definition": {
            "title": "🚨 Detection Rules Status",
            "title_align": "left",
            "type": "group",
            "background_color": "yellow",
            "layout_type": "ordered",
            "widgets": [
                # Detection Rule Indicators
                {
                    "definition": {
                        "title": "Hallucination Rate",
                        "title_size": "16",
                        "title_align": "left",
                        "type": "query_value",
                        "requests": [
                            {
                                "response_format": "scalar",
                                "queries": [
                                    {
                                        "data_source": "metrics",
                                        "name": "query1",
                                        "query": "avg:llm.recommendation.invalid_product_rate{*}",
                                        "aggregator": "avg"
                                    }
                                ],
                                "formulas": [{"formula": "query1 * 100"}],
                                "conditional_formats": [
                                    {"comparator": ">=", "value": 2, "palette": "white_on_red"},
                                    {"comparator": ">=", "value": 1, "palette": "white_on_yellow"},
                                    {"comparator": "<", "value": 1, "palette": "white_on_green"}
                                ]
                            }
                        ],
                        "precision": 2,
                        "custom_unit": "%",
                        "timeseries_background": {"type": "area"}
                    },
                    "layout": {"x": 0, "y": 0, "width": 3, "height": 2}
                },
                {
                    "definition": {
                        "title": "Injection Score (Max)",
                        "title_size": "16",
                        "title_align": "left",
                        "type": "query_value",
                        "requests": [
                            {
                                "response_format": "scalar",
                                "queries": [
                                    {
                                        "data_source": "metrics",
                                        "name": "query1",
                                        "query": "max:llm.security.injection_attempt_score{*}",
                                        "aggregator": "max"
                                    }
                                ],
                                "formulas": [{"formula": "query1"}],
                                "conditional_formats": [
                                    {"comparator": ">=", "value": 0.7, "palette": "white_on_red"},
                                    {"comparator": ">=", "value": 0.5, "palette": "white_on_yellow"},
                                    {"comparator": "<", "value": 0.5, "palette": "white_on_green"}
                                ]
                            }
                        ],
                        "precision": 2,
                        "timeseries_background": {"type": "area"}
                    },
                    "layout": {"x": 3, "y": 0, "width": 3, "height": 2}
                },
                {
                    "definition": {
                        "title": "Error Prediction",
                        "title_size": "16",
                        "title_align": "left",
                        "type": "query_value",
                        "requests": [
                            {
                                "response_format": "scalar",
                                "queries": [
                                    {
                                        "data_source": "metrics",
                                        "name": "query1",
                                        "query": "avg:llm.prediction.error_probability{*}",
                                        "aggregator": "avg"
                                    }
                                ],
                                "formulas": [{"formula": "query1 * 100"}],
                                "conditional_formats": [
                                    {"comparator": ">=", "value": 80, "palette": "white_on_red"},
                                    {"comparator": ">=", "value": 60, "palette": "white_on_yellow"},
                                    {"comparator": "<", "value": 60, "palette": "white_on_green"}
                                ]
                            }
                        ],
                        "precision": 0,
                        "custom_unit": "%",
                        "timeseries_background": {"type": "area"}
                    },
                    "layout": {"x": 6, "y": 0, "width": 3, "height": 2}
                },
                {
                    "definition": {
                        "title": "Monitor Status",
                        "title_size": "16",
                        "title_align": "left",
                        "type": "manage_status",
                        "display_format": "countsAndList",
                        "color_preference": "text",
                        "hide_zero_counts": False,
                        "show_last_triggered": True,
                        "query": "tag:(detection_rule:*)",
                        "sort": "status,asc",
                        "count": 10,
                        "start": 0,
                        "summary_type": "monitors"
                    },
                    "layout": {"x": 9, "y": 0, "width": 3, "height": 2}
                },
                # Detection Metrics Charts
                {
                    "definition": {
                        "title": "Hallucination Rate Over Time",
                        "title_size": "16",
                        "title_align": "left",
                        "show_legend": True,
                        "type": "timeseries",
                        "requests": [
                            {
                                "formulas": [{"formula": "query1"}],
                                "queries": [
                                    {
                                        "data_source": "metrics",
                                        "name": "query1",
                                        "query": "avg:llm.recommendation.invalid_product_rate{*}"
                                    }
                                ],
                                "response_format": "timeseries",
                                "style": {"palette": "orange", "line_type": "solid", "line_width": "normal"},
                                "display_type": "line"
                            }
                        ],
                        "yaxis": {"min": "0", "max": "0.1"},
                        "markers": [
                            {"value": "y = 0.02", "display_type": "error dashed", "label": "Threshold (2%)"}
                        ]
                    },
                    "layout": {"x": 0, "y": 2, "width": 6, "height": 3}
                },
                {
                    "definition": {
                        "title": "Prompt Injection Attempt Score",
                        "title_size": "16",
                        "title_align": "left",
                        "show_legend": True,
                        "type": "timeseries",
                        "requests": [
                            {
                                "formulas": [{"formula": "query1"}],
                                "queries": [
                                    {
                                        "data_source": "metrics",
                                        "name": "query1",
                                        "query": "max:llm.security.injection_attempt_score{*}"
                                    }
                                ],
                                "response_format": "timeseries",
                                "style": {"palette": "red", "line_type": "solid", "line_width": "normal"},
                                "display_type": "line"
                            }
                        ],
                        "yaxis": {"min": "0", "max": "1"},
                        "markers": [
                            {"value": "y = 0.7", "display_type": "error dashed", "label": "Critical (0.7)"},
                            {"value": "y = 0.5", "display_type": "warning dashed", "label": "Warning (0.5)"}
                        ]
                    },
                    "layout": {"x": 6, "y": 2, "width": 6, "height": 3}
                }
            ]
        },
        "layout": {"x": 0, "y": 18, "width": 12, "height": 6}
    })
    
    # ============================================
    # SECTION 4: AI Insights Panel
    # ============================================
    widgets.append({
        "definition": {
            "title": "🔮 AI-Powered Insights",
            "title_align": "left",
            "type": "group",
            "background_color": "orange",
            "layout_type": "ordered",
            "widgets": [
                {
                    "definition": {
                        "type": "note",
                        "content": "**AI Observing AI** 🧠\n\nThe Observability Insights Service uses Gemini to predict errors before they happen and suggest cost optimizations.",
                        "background_color": "transparent",
                        "font_size": "14",
                        "text_align": "left",
                        "vertical_align": "center",
                        "show_tick": False,
                        "tick_pos": "50%",
                        "tick_edge": "left",
                        "has_padding": True
                    },
                    "layout": {"x": 0, "y": 0, "width": 4, "height": 2}
                },
                {
                    "definition": {
                        "title": "Error Risk Level",
                        "title_size": "16",
                        "title_align": "left",
                        "type": "query_value",
                        "requests": [
                            {
                                "response_format": "scalar",
                                "queries": [
                                    {
                                        "data_source": "metrics",
                                        "name": "query1",
                                        "query": "avg:llm.prediction.error_probability{*}",
                                        "aggregator": "last"
                                    }
                                ],
                                "formulas": [{"formula": "query1 * 100"}],
                                "conditional_formats": [
                                    {"comparator": ">=", "value": 80, "palette": "white_on_red"},
                                    {"comparator": ">=", "value": 60, "palette": "white_on_yellow"},
                                    {"comparator": "<", "value": 60, "palette": "white_on_green"}
                                ]
                            }
                        ],
                        "precision": 0,
                        "custom_unit": "%",
                        "timeseries_background": {"type": "area"}
                    },
                    "layout": {"x": 4, "y": 0, "width": 2, "height": 2}
                },
                {
                    "definition": {
                        "title": "24h Cost Forecast",
                        "title_size": "16",
                        "title_align": "left",
                        "type": "query_value",
                        "requests": [
                            {
                                "response_format": "scalar",
                                "queries": [
                                    {
                                        "data_source": "metrics",
                                        "name": "query1",
                                        "query": "avg:llm.prediction.cost_forecast_24h{*}",
                                        "aggregator": "last"
                                    }
                                ],
                                "formulas": [{"formula": "query1"}]
                            }
                        ],
                        "precision": 2,
                        "custom_unit": "$",
                        "timeseries_background": {"type": "area"}
                    },
                    "layout": {"x": 6, "y": 0, "width": 2, "height": 2}
                },
                {
                    "definition": {
                        "title": "Error Probability Trend",
                        "title_size": "16",
                        "title_align": "left",
                        "show_legend": True,
                        "type": "timeseries",
                        "requests": [
                            {
                                "formulas": [{"formula": "query1"}],
                                "queries": [
                                    {
                                        "data_source": "metrics",
                                        "name": "query1",
                                        "query": "avg:llm.prediction.error_probability{*}"
                                    }
                                ],
                                "response_format": "timeseries",
                                "style": {"palette": "orange", "line_type": "solid", "line_width": "thick"},
                                "display_type": "line"
                            }
                        ],
                        "yaxis": {"min": "0", "max": "1"},
                        "markers": [
                            {"value": "y = 0.8", "display_type": "error dashed", "label": "Alert Threshold"}
                        ]
                    },
                    "layout": {"x": 8, "y": 0, "width": 4, "height": 2}
                }
            ]
        },
        "layout": {"x": 0, "y": 24, "width": 12, "height": 3}
    })
    
    # ============================================
    # SECTION 5: LLM Services Deep Dive
    # ============================================
    widgets.append({
        "definition": {
            "title": "🛍️ LLM Services Deep Dive",
            "title_align": "left",
            "type": "group",
            "background_color": "green",
            "layout_type": "ordered",
            "widgets": [
                {
                    "definition": {
                        "title": "Chatbot Service Requests",
                        "title_size": "16",
                        "title_align": "left",
                        "show_legend": True,
                        "type": "timeseries",
                        "requests": [
                            {
                                "formulas": [{"formula": "query1"}],
                                "queries": [
                                    {
                                        "data_source": "metrics",
                                        "name": "query1",
                                        "query": "sum:trace.grpc.request.hits{service:chatbotservice}.as_rate()"
                                    }
                                ],
                                "response_format": "timeseries",
                                "style": {"palette": "dog_classic", "line_type": "solid", "line_width": "normal"},
                                "display_type": "line"
                            }
                        ]
                    },
                    "layout": {"x": 0, "y": 0, "width": 4, "height": 3}
                },
                {
                    "definition": {
                        "title": "PEAU Agent Requests",
                        "title_size": "16",
                        "title_align": "left",
                        "show_legend": True,
                        "type": "timeseries",
                        "requests": [
                            {
                                "formulas": [{"formula": "query1"}],
                                "queries": [
                                    {
                                        "data_source": "metrics",
                                        "name": "query1",
                                        "query": "sum:trace.grpc.request.hits{service:peau-agent OR service:peau_agent}.as_rate()"
                                    }
                                ],
                                "response_format": "timeseries",
                                "style": {"palette": "cool", "line_type": "solid", "line_width": "normal"},
                                "display_type": "line"
                            }
                        ]
                    },
                    "layout": {"x": 4, "y": 0, "width": 4, "height": 3}
                },
                {
                    "definition": {
                        "title": "Shopping Assistant Requests",
                        "title_size": "16",
                        "title_align": "left",
                        "show_legend": True,
                        "type": "timeseries",
                        "requests": [
                            {
                                "formulas": [{"formula": "query1"}],
                                "queries": [
                                    {
                                        "data_source": "metrics",
                                        "name": "query1",
                                        "query": "sum:trace.grpc.request.hits{service:shoppingassistantservice}.as_rate()"
                                    }
                                ],
                                "response_format": "timeseries",
                                "style": {"palette": "purple", "line_type": "solid", "line_width": "normal"},
                                "display_type": "line"
                            }
                        ]
                    },
                    "layout": {"x": 8, "y": 0, "width": 4, "height": 3}
                },
                # Token usage by service
                {
                    "definition": {
                        "title": "Token Usage by Service",
                        "title_size": "16",
                        "title_align": "left",
                        "type": "toplist",
                        "requests": [
                            {
                                "formulas": [{"formula": "query1", "limit": {"count": 10, "order": "desc"}}],
                                "queries": [
                                    {
                                        "data_source": "metrics",
                                        "name": "query1",
                                        "query": "sum:llm.tokens.input{*} by {service}.as_count()",
                                        "aggregator": "sum"
                                    }
                                ],
                                "response_format": "scalar"
                            }
                        ]
                    },
                    "layout": {"x": 0, "y": 3, "width": 6, "height": 3}
                },
                {
                    "definition": {
                        "title": "LLM Cost by Service",
                        "title_size": "16",
                        "title_align": "left",
                        "type": "toplist",
                        "requests": [
                            {
                                "formulas": [{"formula": "query1", "limit": {"count": 10, "order": "desc"}}],
                                "queries": [
                                    {
                                        "data_source": "metrics",
                                        "name": "query1",
                                        "query": "sum:llm.tokens.total_cost_usd{*} by {service}",
                                        "aggregator": "sum"
                                    }
                                ],
                                "response_format": "scalar"
                            }
                        ]
                    },
                    "layout": {"x": 6, "y": 3, "width": 6, "height": 3}
                }
            ]
        },
        "layout": {"x": 0, "y": 27, "width": 12, "height": 7}
    })
    
    return widgets


def main():
    """Main function to create the LLM Observability Dashboard."""
    print("=" * 60)
    print("🐕 V-Commerce Datadog Dashboard Creator")
    print("=" * 60)
    print()
    
    # Validate credentials
    if not validate_credentials():
        sys.exit(1)
    
    print()
    print("📊 Creating V-Commerce LLM Observability Dashboard...")
    print("-" * 40)
    
    dashboard_config = get_llm_observability_dashboard()
    
    try:
        result = create_dashboard(dashboard_config)
        
        if "id" in result:
            dashboard_id = result["id"]
            
            print(f"\n✅ Dashboard created successfully!")
            print(f"   ID: {dashboard_id}")
            print(f"   Title: {dashboard_config['title']}")
            print()
            print(f"🔗 View dashboard at:")
            print(f"   https://app.{DD_SITE}{result.get('url', '/dashboard/' + dashboard_id)}")
            print()
            
            # Save dashboard info to file
            output = {
                "id": dashboard_id,
                "title": dashboard_config["title"],
                "url": f"https://app.{DD_SITE}{result.get('url', '/dashboard/' + dashboard_id)}",
                "created_at": result.get("created_at", ""),
                "author_handle": result.get("author_handle", "")
            }
            
            output_file = "datadog-exports/created-dashboard.json"
            with open(output_file, "w") as f:
                json.dump(output, f, indent=2)
            print(f"💾 Dashboard info saved to: {output_file}")
            
            # Also save the full dashboard definition for reference
            definition_file = "datadog-exports/dashboards/llm-observability-dashboard.json"
            os.makedirs(os.path.dirname(definition_file), exist_ok=True)
            with open(definition_file, "w") as f:
                json.dump(dashboard_config, f, indent=2)
            print(f"💾 Dashboard definition saved to: {definition_file}")
            
            return True
            
        elif "errors" in result:
            error_msg = result["errors"]
            print(f"\n❌ Failed to create dashboard: {error_msg}")
            
            if "Forbidden" in str(error_msg):
                print(f"\n💡 Your Application Key needs 'dashboards_write' scope.")
                print(f"   Create a new key at: https://app.{DD_SITE}/personal-settings/application-keys")
            
            return False
        else:
            print(f"\n⚠️ Unexpected response: {result}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error creating dashboard: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
