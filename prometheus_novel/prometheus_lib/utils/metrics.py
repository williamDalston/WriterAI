# Monitoring and metrics utilities
import time
from collections import defaultdict
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Simple in-memory metrics store for demonstration
_metrics_data: Dict[str, Any] = defaultdict(lambda: {"count": 0, "sum": 0.0, "last_value": None, "timestamps": []})

def increment_counter(name: str, value: int = 1):
    '''Increments a counter metric.'''
    _metrics_data[name]["count"] += value
    logger.debug(f"Metric '{name}' incremented to {_metrics_data[name]['count']}")

def gauge(name: str, value: float):
    '''Sets a gauge metric to a specific value.'''
    _metrics_data[name]["last_value"] = value
    logger.debug(f"Metric '{{name}}' set to {{value}}")

def observe_latency(name: str, start_time: float):
    '''Records latency for an operation.'''
    latency = time.time() - start_time
    _metrics_data[name]["sum"] += latency
    _metrics_data[name]["count"] += 1
    _metrics_data[name]["timestamps"].append(latency) # Store for p95/p99 calculation
    logger.debug(f"Metric '{{name}}' observed latency: {{latency:.4f}}s")

def get_metrics_snapshot() -> Dict[str, Any]:
    '''Returns a snapshot of current metrics.'''
    snapshot = {}
    for name, data in _metrics_data.items():
        if "timestamps" in data and data["count"] > 0:
            latencies = sorted(data["timestamps"])
            p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0
            p99 = latencies[int(len(latencies) * 0.99)] if latencies else 0
            snapshot[name] = {
                "count": data["count"],
                "sum": data["sum"],
                "avg_latency": data["sum"] / data["count"] if data["count"] > 0 else 0,
                "p95_latency": p95,
                "p99_latency": p99,
                "last_value": data.get("last_value")
            }
        else:
            snapshot[name] = data
    return snapshot

def reset_metrics():
    '''Resets all metrics.'''
    _metrics_data.clear()
    logger.info("All metrics reset.")

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    
    increment_counter("api_calls_total")
    gauge("current_budget_usd", 500.0)
    
    start = time.time()
    time.sleep(0.05)
    observe_latency("llm_call_latency", start)

    start = time.time()
    time.sleep(0.12)
    observe_latency("llm_call_latency", start)

    increment_counter("api_calls_total", 2)

    snapshot = get_metrics_snapshot()
    print("\nMetrics Snapshot:")
    import json
    print(json.dumps(snapshot, indent=2))

    reset_metrics()
    print("\nMetrics after reset:", get_metrics_snapshot())
