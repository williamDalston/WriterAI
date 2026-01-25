# 🔌 AGENT-06 Integration Guide

**Quick guide for integrating AGENT-06 enhancements into your pipeline**

---

## ✅ Integration Complete!

All AGENT-06 features have been integrated into `PrometheusServiceContainer`. Here's how to use them:

---

## 🚀 Quick Start

### 1. Service Container Now Includes:

```python
from prometheus_lib.services.service_container_impl import PrometheusServiceContainer

# Initialize service container (same as before)
config = {...}  # Your config dict
services = PrometheusServiceContainer(config)

# NEW: Initialize async services (memory persistence, etc.)
await services.initialize_async()

# Use enhanced features:
# - services.cost_tracker (enhanced with prediction/alerts)
# - services.memory_engine (with persistence)
# - services.memory_persistence (automatic saving/loading)
# - services.performance_profiler (bottleneck detection)
# - services.performance_optimizer (optimization recommendations)
# - services.parallel_executor (parallel execution)
# - services.context_minifier (token optimization)
```

---

## 📝 Usage Examples

### Cost Tracking with Alerts

```python
# Cost tracker is already initialized with budget
# It will automatically alert at 50%, 75%, and 100% of budget

# Estimate cost before operation
estimated = services.cost_tracker.estimate_cost(
    model_name="gpt-4o-mini",
    estimated_input_tokens=1000,
    estimated_output_tokens=500
)

# Predict total cost for remaining stages
predicted = services.cost_tracker.predict_total_cost(
    current_cost=state.total_cost_usd,
    remaining_stages=[
        ("stage_6", "gpt-4o-mini", 1000, 500),
        ("stage_7", "gpt-4o-mini", 800, 400)
    ]
)

# Get cost breakdown
breakdown = services.cost_tracker.get_cost_breakdown()
print(f"Total: ${breakdown['total_cost']:.2f}")
print(f"By stage: {breakdown['by_stage']}")
print(f"By model: {breakdown['by_model']}")
```

### Memory Persistence

```python
# Memory persistence is automatically initialized
# Memory is automatically saved when added

# Manual save (optional, auto-save is enabled)
await services.memory_persistence.save()

# Create backup
backup_path = await services.memory_persistence.create_backup()

# Get statistics
stats = services.memory_persistence.get_statistics()
print(f"Backups: {stats['backup_count']}")
print(f"Last backup: {stats['last_backup_time']}")

# Shutdown (saves final state)
await services.memory_persistence.shutdown()
```

### Performance Profiling

```python
from prometheus_lib.optimization import OperationType

# Profile an operation
services.performance_profiler.start_operation(
    "scene_generation",
    OperationType.STAGE_EXECUTION,
    "generate_scene_6"
)

# ... do work ...

duration = services.performance_profiler.end_operation(
    "scene_generation",
    OperationType.STAGE_EXECUTION,
    "generate_scene_6"
)

# Analyze bottlenecks
bottlenecks = services.performance_profiler.analyze_bottlenecks()

# Get optimization recommendations
recommendations = services.performance_optimizer.get_optimization_recommendations()
for rec in recommendations:
    print(f"{rec['priority']}: {rec['operation']} - {rec['recommendation']}")
```

### Parallel Execution

```python
from prometheus_lib.optimization import ExecutionTask, ExecutionStrategy

# Execute multiple stages in parallel
tasks = [
    ExecutionTask(
        task_id="stage_6_scene_1",
        func=generate_scene,
        args=(state, services, 0),
        dependencies=[],
        priority=1
    ),
    ExecutionTask(
        task_id="stage_6_scene_2",
        func=generate_scene,
        args=(state, services, 1),
        dependencies=[],
        priority=1
    )
]

results = await services.parallel_executor.execute_parallel(
    tasks,
    strategy=ExecutionStrategy.PARALLEL
)
```

### Context Minification

```python
# Minify context to fit token budget
minified = services.context_minifier.minify_context(
    context={
        "story_bible": long_story_bible_text,
        "previous_scene": long_previous_scene_text,
        "character_profiles": character_data
    },
    important_keys=["story_bible"]  # Preserve these
)

# Use minified context in LLM call
prompt = build_prompt(minified)
```

---

## 🔧 Configuration

Add these to your config YAML:

```yaml
# Cost tracking
budget_usd: 50.0  # Budget in USD

# Memory persistence
use_distributed_store: true
redis_url: "redis://localhost:6379"  # Or your Redis URL

# Performance
max_concurrency: 10  # Max parallel operations
context_max_tokens: 2000  # Max tokens in context
```

---

## 📊 Monitoring

### Check Cost Status

```python
# Get current cost status
within_budget, warning = services.cost_tracker.check_budget(state.total_cost_usd)
if not within_budget:
    print(f"BUDGET EXCEEDED: {warning}")
elif warning:
    print(f"Warning: {warning}")

# Get detailed breakdown
breakdown = services.cost_tracker.get_cost_breakdown()
```

### Check Performance

```python
# Get performance statistics
stats = services.performance_profiler.get_statistics()
print(f"Total operations: {stats['total_operations']}")
print(f"Total time: {stats['total_time_seconds']:.2f}s")
print(f"Top bottlenecks: {stats['top_bottlenecks']}")
```

### Check Memory

```python
# Get memory statistics
stats = await services.memory_engine.get_memory_statistics()
print(f"Immediate: {stats['immediate_count']}")
print(f"Recent: {stats['recent_count']}")
print(f"Archival: {stats['archival_count']}")
```

---

## 🎯 Best Practices

1. **Always call `initialize_async()`** after creating service container
2. **Call `shutdown()`** before application exit to save final state
3. **Use cost prediction** before expensive operations
4. **Profile critical operations** to identify bottlenecks
5. **Use parallel execution** for independent stages
6. **Minify context** for large prompts to reduce costs

---

## 🐛 Troubleshooting

### Memory Persistence Not Working

- Check Redis is running: `redis-cli ping`
- Check Redis URL in config
- Check logs for connection errors

### Cost Alerts Not Firing

- Verify budget is set in config
- Check alert thresholds are configured
- Verify cost tracker is being used

### Performance Profiling Not Showing Data

- Ensure you're calling `start_operation()` and `end_operation()`
- Check operation types are correct
- Verify profiler is initialized

---

## ✅ Integration Status

- ✅ Enhanced CostTracker integrated
- ✅ MemoryEngine with persistence integrated
- ✅ MemoryPersistence layer integrated
- ✅ PerformanceProfiler integrated
- ✅ PerformanceOptimizer integrated
- ✅ ParallelExecutor integrated
- ✅ ContextMinifier integrated

**All features are ready to use!**

