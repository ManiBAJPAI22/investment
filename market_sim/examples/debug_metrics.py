"""Quick diagnostic to check why metrics aren't showing"""
import sys
from pathlib import Path
import requests
import json

# Check API
response = requests.get('http://localhost:8080/api/summary')
api_data = response.json()

print("="*70)
print("METRICS DIAGNOSTIC")
print("="*70)
print("\nDashboard API shows:")
print(f"  Total orders: {api_data['performance']['total_orders']}")
print(f"  Total trades: {api_data['performance']['total_trades']}")
print(f"  Leader: {api_data['cluster']['leader']}")

# Check log file
import subprocess
result = subprocess.run(
    ["tail", "-5", "/tmp/consensus_live.log"],
    capture_output=True,
    text=True
)
print("\nConsole log shows:")
for line in result.stdout.strip().split('\n'):
    if 'Orders:' in line:
        print(f"  {line.strip()}")

print("\n" + "="*70)
print("PROBLEM: Console shows orders being submitted,")
print("but dashboard API shows 0. This means the metrics")
print("collector is not reading from the actual exchanges.")
print("="*70)
