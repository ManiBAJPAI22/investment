# Real-Time Monitoring Dashboard Demo

## Overview

The monitoring dashboard provides enterprise-grade observability for the distributed consensus cluster.

## Features

### 1. Real-Time Metrics Collection
- Automatic collection every second from all nodes
- Time-series data with 5-minute retention
- Zero performance impact on consensus

### 2. Web Dashboard
- Clean, auto-refreshing UI
- Cluster health overview
- Per-node status display
- Performance metrics visualization
- Alert notifications

### 3. REST API
Complete programmatic access to all metrics:

```bash
# Health check
curl http://localhost:8080/api/health

# Complete summary
curl http://localhost:8080/api/summary

# Historical metrics (last 60 seconds)
curl http://localhost:8080/api/metrics/history?duration=60

# Node-specific metrics
curl http://localhost:8080/api/node?node_id=node1&duration=60

# Active alerts
curl http://localhost:8080/api/alerts
```

## Quick Start

### Simple Test (3 nodes, 5 seconds)
```bash
python3 examples/test_monitoring_quick.py
```

Output:
```
✓ Cluster created, leader: node1
✓ Metrics collector started
[1] Healthy: 3/3, Leader: node1, Status: healthy
...
✓ Health API: healthy
✓ Summary API: 3 nodes
✓ MONITORING TEST COMPLETE
```

### Full Demo (5 nodes, trading simulation, web UI)
```bash
python3 examples/monitoring_demo.py
```

This will:
1. Create 5-node cluster
2. Start metrics collection
3. Launch web dashboard at http://localhost:8080
4. Open browser automatically
5. Run 200-tick trading simulation
6. Inject node failures at ticks 30, 60, 100, 130
7. Display real-time metrics in terminal and web UI

## Metrics Reference

### Cluster Metrics
- `cluster_size`: Total nodes in cluster
- `healthy_nodes`: Nodes currently operational
- `leader_node`: Current leader ID
- `health_status`: HEALTHY | DEGRADED | UNHEALTHY
- `current_term`: Raft term number
- `consensus_aligned`: Boolean indicating consensus agreement

### Performance Metrics
- `total_orders`: Cumulative orders submitted
- `total_trades`: Cumulative trades executed
- `throughput_ops`: Current throughput (orders/second)
- `avg_latency_ms`: Average consensus latency

### Node Metrics (per node)
- `state`: LEADER | FOLLOWER | CANDIDATE
- `commit_index`: Highest committed log index
- `last_applied`: Highest applied log index
- `log_length`: Total log entries
- `peers_connected`: Number of connected peers

## Health Status

The system automatically determines cluster health:

- **HEALTHY**: All nodes operational, leader present, consensus aligned
- **DEGRADED**: Some nodes down but quorum maintained, or minor alignment issues
- **UNHEALTHY**: No leader or quorum lost

## Alerts

Automatic alerts for:
- Cluster becomes unhealthy
- Leader election failure
- Consensus misalignment detected
- Quorum loss

## API Examples

### Python
```python
import requests

# Get summary
response = requests.get('http://localhost:8080/api/summary')
data = response.json()

print(f"Cluster health: {data['cluster']['health_status']}")
print(f"Leader: {data['cluster']['leader']}")
print(f"Throughput: {data['performance']['throughput_ops']} ops/s")
```

### Bash
```bash
# Monitor throughput
while true; do
  curl -s http://localhost:8080/api/summary | \
    jq '.performance.throughput_ops'
  sleep 1
done
```

## Production Usage

For production deployments:

```python
from monitoring import MetricsCollector, DashboardServer

# Create collector with custom settings
collector = MetricsCollector(
    collection_interval=1.0,      # Collect every second
    retention_period=3600,         # Keep 1 hour
    alert_callback=send_to_pagerduty  # Custom alert handler
)

# Set alert thresholds
collector.alert_thresholds = {
    'max_latency_ms': 500,        # Alert if latency > 500ms
    'min_healthy_nodes': 3,       # Alert if < 3 nodes healthy
    'max_term_difference': 2,     # Alert if term spread > 2
}

# Start monitoring
collector.set_cluster(exchanges)
collector.start()

# Start dashboard on custom port
dashboard = DashboardServer(
    collector=collector,
    host='0.0.0.0',  # Listen on all interfaces
    port=9090
)
dashboard.start()
```

## Architecture

```
┌─────────────────┐
│  Web Browser    │
│  (Dashboard UI) │
└────────┬────────┘
         │ HTTP GET /api/*
         ↓
┌─────────────────────┐
│  DashboardServer    │
│  (HTTP + REST API)  │
└────────┬────────────┘
         │
         ↓
┌─────────────────────┐
│  MetricsCollector   │
│  (1s poll interval) │
└────────┬────────────┘
         │
         ↓
┌────────────────────────────────┐
│   Distributed Exchange Cluster  │
│   ┌──────┐ ┌──────┐ ┌──────┐  │
│   │Node1 │ │Node2 │ │Node3 │  │
│   └──────┘ └──────┘ └──────┘  │
└────────────────────────────────┘
```

## Performance

- Collection overhead: <1ms per node
- Memory footprint: ~50MB for 5-minute retention
- API latency: <10ms
- Dashboard refresh: 5 seconds (configurable)

## See Also

- [Chaos Engineering](../tests/chaos/) - Fault injection testing
- [Multi-Raft Sharding](../blockchain/consensus/multi_raft.py) - Horizontal scaling
- [Integration Tests](../tests/integration/) - Test suite
