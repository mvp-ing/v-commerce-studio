#!/usr/bin/env python3
"""
Observability Agent Test Runner

This script:
1. Generates traffic patterns (normal, errors, high load)
2. Queries the Observability Insights Agent
3. Logs all agent responses to timestamped files for review

Usage:
    python3 scripts/obs-agent-test-runner.py --frontend-url http://localhost:8080 --agent-url http://localhost:8089

Output:
    Logs saved to: logs/obs-agent-runs/
"""

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import requests
import subprocess
import sys


class ObsAgentTestRunner:
    """
    Orchestrates traffic generation and observability agent testing.
    """

    def __init__(self, frontend_url: str, agent_url: str, log_dir: str = "logs/obs-agent-runs"):
        self.frontend_url = frontend_url.rstrip("/")
        self.agent_url = agent_url.rstrip("/")
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create run-specific directory
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_dir = self.log_dir / self.run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"📁 Logs will be saved to: {self.run_dir}")
    
    def _log_response(self, endpoint: str, response: Dict[str, Any], scenario: str = ""):
        """Save agent response to a log file"""
        safe_endpoint = endpoint.replace("/", "_").strip("_")
        filename = f"{scenario}_{safe_endpoint}.json" if scenario else f"{safe_endpoint}.json"
        filepath = self.run_dir / filename
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "endpoint": endpoint,
            "scenario": scenario,
            "response": response
        }
        
        with open(filepath, "w") as f:
            json.dump(log_entry, f, indent=2)
        
        print(f"  💾 Logged to: {filepath.name}")
    
    def _call_agent(self, endpoint: str, method: str = "GET", data: Dict = None, timeout: int = 120) -> Optional[Dict]:
        """Call an observability agent endpoint"""
        url = f"{self.agent_url}{endpoint}"
        try:
            if method == "GET":
                resp = requests.get(url, timeout=timeout)
            else:
                resp = requests.post(url, json=data, timeout=timeout, headers={"Content-Type": "application/json"})
            return resp.json()
        except Exception as e:
            print(f"  ❌ Error calling {endpoint}: {e}")
            return {"error": str(e)}
    
    def _run_traffic_generator(self, scenario: str, duration: int = 30, count: int = 10):
        """Run the traffic generator with a specific scenario"""
        print(f"\n🚗 Running traffic generator: {scenario}")
        
        cmd = [
            sys.executable, "scripts/traffic-generator.py",
            "--base-url", self.frontend_url,
            "--scenario", scenario,
            "--duration-seconds", str(duration)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=duration + 60)
            print(f"  ✅ Traffic generation complete")
            return True
        except subprocess.TimeoutExpired:
            print(f"  ⏰ Traffic generation timed out")
            return False
        except Exception as e:
            print(f"  ❌ Traffic generation failed: {e}")
            return False

    # =========================================
    # Test Scenarios
    # =========================================
    
    def test_quick_health_check(self, scenario: str = "baseline") -> Dict:
        """Test the quick health check endpoint (FREE - no LLM tokens)"""
        print(f"\n🩺 Testing: Quick Health Check")
        response = self._call_agent("/insights/quick-check")
        self._log_response("quick-check", response, scenario)
        
        if response and "result" in response:
            concerns = response.get("result", {}).get("concerns", [])
            needs_analysis = response.get("result", {}).get("needs_deep_analysis", False)
            print(f"  📊 Concerns: {len(concerns)}, Needs deep analysis: {needs_analysis}")
        
        return response
    
    def test_error_prediction(self, scenario: str = "baseline", force: bool = True) -> Dict:
        """Test the error prediction endpoint"""
        print(f"\n🔮 Testing: Error Prediction (force={force})")
        endpoint = f"/insights/errors?force={'true' if force else 'false'}"
        response = self._call_agent(endpoint)
        self._log_response("error-prediction", response, scenario)
        
        if response and "result" in response:
            agent_response = response.get("result", {}).get("response", "")
            duration = response.get("result", {}).get("duration_ms", 0)
            print(f"  ⏱️ Duration: {duration:.0f}ms")
            print(f"  📝 Response: {agent_response[:200]}..." if len(agent_response) > 200 else f"  📝 Response: {agent_response}")
        
        return response
    
    def test_deep_error_prediction(self, scenario: str = "deep_analysis") -> Dict:
        """
        Test deep error prediction using a custom task.
        This ALWAYS performs full analysis and makes predictions.
        """
        print(f"\n🔮 Testing: DEEP Error Prediction (always runs full analysis)")
        
        deep_prediction_task = """Perform a complete error prediction analysis:

1. Call get_quick_health_check() - get current status
2. Call get_error_metrics() - analyze latency and error trends
3. Call get_full_llm_metrics('chatbotservice') - get LLM metrics

Then analyze the data and:
- Calculate probability of issues in next 2 hours (0-100%)
- Emit metric "llm.prediction.error_probability" with your prediction (0.0 to 1.0)
- If probability > 30%, send a warning event to Datadog

Provide your response in this format:
ERROR PROBABILITY: X% (next 2 hours)
CONFIDENCE: high/medium/low
RISK FACTORS:
- factor 1
- factor 2
RECOMMENDED ACTIONS:
- action 1
- action 2
"""
        response = self._call_agent("/agent/chat", method="POST", data={"task": deep_prediction_task})
        self._log_response("deep-error-prediction", response, scenario)
        
        if response and "result" in response:
            agent_response = response.get("result", {}).get("response", "")
            duration = response.get("result", {}).get("duration_ms", 0)
            print(f"  ⏱️ Duration: {duration:.0f}ms")
            print(f"  📝 Response: {agent_response[:300]}..." if len(agent_response) > 300 else f"  📝 Response: {agent_response}")
        
        return response
    
    def test_cost_analysis(self, scenario: str = "baseline") -> Dict:
        """Test the cost analysis endpoint"""
        print(f"\n💰 Testing: Cost Analysis")
        response = self._call_agent("/insights/costs")
        self._log_response("cost-analysis", response, scenario)
        
        if response and "result" in response:
            agent_response = response.get("result", {}).get("response", "")
            duration = response.get("result", {}).get("duration_ms", 0)
            print(f"  ⏱️ Duration: {duration:.0f}ms")
            print(f"  📝 Response: {agent_response[:200]}..." if len(agent_response) > 200 else f"  📝 Response: {agent_response}")
        
        return response
    
    def test_health_summary(self, scenario: str = "baseline") -> Dict:
        """Test the health summary endpoint"""
        print(f"\n📊 Testing: Health Summary")
        response = self._call_agent("/insights/health")
        self._log_response("health-summary", response, scenario)
        
        if response and "result" in response:
            agent_response = response.get("result", {}).get("response", "")
            duration = response.get("result", {}).get("duration_ms", 0)
            print(f"  ⏱️ Duration: {duration:.0f}ms")
            print(f"  📝 Response: {agent_response[:200]}..." if len(agent_response) > 200 else f"  📝 Response: {agent_response}")
        
        return response
    
    def test_natural_language(self, task: str, scenario: str = "custom") -> Dict:
        """Test the natural language chat endpoint"""
        print(f"\n💬 Testing: Natural Language Chat")
        print(f"  📝 Task: {task}")
        response = self._call_agent("/agent/chat", method="POST", data={"task": task})
        self._log_response("chat", response, scenario)
        
        if response and "result" in response:
            agent_response = response.get("result", {}).get("response", "")
            duration = response.get("result", {}).get("duration_ms", 0)
            print(f"  ⏱️ Duration: {duration:.0f}ms")
            print(f"  📝 Response: {agent_response[:200]}..." if len(agent_response) > 200 else f"  📝 Response: {agent_response}")
        
        return response

    # =========================================
    # Full Test Runs
    # =========================================
    
    def run_baseline_test(self):
        """Run baseline tests without error injection"""
        print("\n" + "="*60)
        print("📋 BASELINE TEST (No errors)")
        print("="*60)
        
        # Generate normal traffic first
        self._run_traffic_generator("normal", duration=30)
        
        # Wait for metrics to propagate
        print("\n⏳ Waiting 10s for metrics to propagate...")
        time.sleep(10)
        
        # Run all agent tests
        self.test_quick_health_check("baseline")
        self.test_error_prediction("baseline")
        self.test_cost_analysis("baseline")
        self.test_health_summary("baseline")
    
    def run_error_injection_test(self):
        """Run test with error-inducing traffic to trigger predictions"""
        print("\n" + "="*60)
        print("🔴 ERROR INJECTION TEST")
        print("="*60)
        
        # Generate error-inducing traffic
        self._run_traffic_generator("error", duration=30)
        
        # Wait for metrics to propagate
        print("\n⏳ Waiting 10s for metrics to propagate...")
        time.sleep(10)
        
        # Run agent tests  
        self.test_quick_health_check("after_errors")
        self.test_error_prediction("after_errors", force=True)
        self.test_health_summary("after_errors")
    
    def run_latency_spike_test(self):
        """Run test with latency-inducing traffic"""
        print("\n" + "="*60)
        print("🔶 LATENCY/QUALITY DEGRADATION TEST")
        print("="*60)
        
        # Generate latency-inducing traffic
        self._run_traffic_generator("latency_quality", duration=30)
        
        # Wait for metrics to propagate
        print("\n⏳ Waiting 10s for metrics to propagate...")
        time.sleep(10)
        
        # Run agent tests
        self.test_quick_health_check("after_latency")
        self.test_error_prediction("after_latency", force=True)
        self.test_health_summary("after_latency")
    
    def run_cost_spike_test(self):
        """Run test with high token usage"""
        print("\n" + "="*60)
        print("💸 COST SPIKE TEST")
        print("="*60)
        
        # Generate high-cost traffic (reduced to minimize API costs)
        self._run_traffic_generator("cost", duration=30)
        
        # Wait for metrics to propagate
        print("\n⏳ Waiting 10s for metrics to propagate...")
        time.sleep(10)
        
        # Run agent tests
        self.test_cost_analysis("after_cost_spike")
        self.test_health_summary("after_cost_spike")
    
    def run_full_simulation(self):
        """Run a complete simulation with all scenarios"""
        print("\n" + "="*60)
        print("🚀 FULL SIMULATION RUN")
        print("="*60)
        print(f"📁 All logs saved to: {self.run_dir}")
        
        start_time = time.time()
        
        # Phase 1: Baseline
        self.run_baseline_test()
        
        # Phase 2: Error injection
        self.run_error_injection_test()
        
        # Phase 3: Latency spike
        self.run_latency_spike_test()
        
        # Phase 4: Cost analysis
        self.run_cost_spike_test()
        
        # Final summary
        total_time = time.time() - start_time
        print("\n" + "="*60)
        print("✅ SIMULATION COMPLETE")
        print("="*60)
        print(f"⏱️ Total time: {total_time:.1f}s")
        print(f"📁 Logs saved to: {self.run_dir}")
        print(f"📊 Files generated: {len(list(self.run_dir.glob('*.json')))}")
    
    def run_quick_test(self):
        """Run a quick test with minimal traffic (for demo)"""
        print("\n" + "="*60)
        print("⚡ QUICK TEST (Minimal traffic)")
        print("="*60)
        print(f"📁 Logs saved to: {self.run_dir}")
        
        # Just run agent tests without traffic generation
        self.test_quick_health_check("quick")
        self.test_error_prediction("quick", force=True)
        self.test_health_summary("quick")
        
        print("\n✅ Quick test complete!")
        print(f"📁 Logs saved to: {self.run_dir}")
    
    def run_prediction_test(self):
        """Run deep error prediction test with traffic that creates concerning patterns"""
        print("\n" + "="*60)
        print("🔮 DEEP ERROR PREDICTION TEST")
        print("="*60)
        print(f"📁 Logs saved to: {self.run_dir}")
        
        # Generate some error traffic to create concerning metrics
        print("\n📊 Phase 1: Generating error traffic...")
        self._run_traffic_generator("error", duration=20)
        
        # Wait for metrics to propagate
        print("\n⏳ Waiting 15s for metrics to propagate to Datadog...")
        time.sleep(15)
        
        # Run deep error prediction
        print("\n📊 Phase 2: Running DEEP Error Prediction...")
        self.test_deep_error_prediction("after_error_traffic")
        
        # Also run health summary for comparison
        self.test_health_summary("after_error_traffic")
        
        print("\n✅ Prediction test complete!")
        print(f"📁 Logs saved to: {self.run_dir}")
    
    def run_quality_degradation_test(self):
        """Run quality degradation test for Rule 4 detection"""
        print("\n" + "="*60)
        print("📉 QUALITY DEGRADATION TEST (Rule 4)")
        print("="*60)
        print(f"📁 Logs saved to: {self.run_dir}")
        
        # Generate quality-degrading traffic
        print("\n📊 Phase 1: Generating low-quality prompts...")
        self._run_traffic_generator("quality", duration=30)
        
        # Wait for metrics to propagate
        print("\n⏳ Waiting 15s for metrics to propagate...")
        time.sleep(15)
        
        # Run agent to analyze quality
        print("\n📊 Phase 2: Running quality analysis...")
        task = """Analyze the current llm.response.quality_score metric:
1. Call get_full_llm_metrics('chatbotservice') to get quality scores
2. Report the average quality score
3. If average quality < 0.7, this indicates a quality degradation alert should trigger
4. Recommend actions to improve response quality

Report the quality score and any concerns."""
        
        response = self._call_agent("/agent/chat", method="POST", data={"task": task})
        self._log_response("quality-analysis", response, "after_quality_degradation")
        
        if response and "result" in response:
            agent_response = response.get("result", {}).get("response", "")
            duration = response.get("result", {}).get("duration_ms", 0)
            print(f"  ⏱️ Duration: {duration:.0f}ms")
            print(f"  📝 Response: {agent_response[:300]}..." if len(agent_response) > 300 else f"  📝 Response: {agent_response}")
        
        # Also run health summary
        self.test_health_summary("after_quality_degradation")
        
        print("\n✅ Quality degradation test complete!")
        print(f"📁 Logs saved to: {self.run_dir}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run observability agent tests with traffic generation and response logging."
    )
    parser.add_argument(
        "--frontend-url",
        default="http://localhost:8080",
        help="Frontend URL for traffic generation (default: http://localhost:8080)"
    )
    parser.add_argument(
        "--agent-url",
        default="http://localhost:8089",
        help="Observability Agent URL (default: http://localhost:8089)"
    )
    parser.add_argument(
        "--mode",
        choices=["quick", "baseline", "errors", "latency", "cost", "full", "predict", "quality"],
        default="quick",
        help="Test mode to run (default: quick)"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    runner = ObsAgentTestRunner(args.frontend_url, args.agent_url)
    
    if args.mode == "quick":
        runner.run_quick_test()
    elif args.mode == "baseline":
        runner.run_baseline_test()
    elif args.mode == "errors":
        runner.run_error_injection_test()
    elif args.mode == "latency":
        runner.run_latency_spike_test()
    elif args.mode == "cost":
        runner.run_cost_spike_test()
    elif args.mode == "full":
        runner.run_full_simulation()
    elif args.mode == "predict":
        runner.run_prediction_test()
    elif args.mode == "quality":
        runner.run_quality_degradation_test()


if __name__ == "__main__":
    main()

