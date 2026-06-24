import argparse
import json
import time
from datetime import datetime

import requests


def run_benchmark(endpoint, model_name, num_requests, prompt, api_key=None):
    results = []
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    for i in range(num_requests):
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 128,
        }
        start = time.time()
        resp = requests.post(
            f"{endpoint}/v1/chat/completions",
            json=payload,
            headers=headers,
        )
        latency = time.time() - start
        results.append({
            "request_id": i + 1,
            "status_code": resp.status_code,
            "latency_s": round(latency, 4),
        })
        print(f"[{i+1}/{num_requests}] status={resp.status_code} latency={latency:.4f}s")

    latencies = [r["latency_s"] for r in results if r["status_code"] == 200]
    summary = {
        "model": model_name,
        "endpoint": endpoint,
        "num_requests": num_requests,
        "successful": len(latencies),
        "avg_latency_s": round(sum(latencies) / len(latencies), 4) if latencies else 0,
        "min_latency_s": round(min(latencies), 4) if latencies else 0,
        "max_latency_s": round(max(latencies), 4) if latencies else 0,
        "timestamp": datetime.now().isoformat(),
        "details": results,
    }

    output_path = f"/app/results/benchmark_{model_name.replace('/', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nResults saved to {output_path}")
    print(f"Avg latency: {summary['avg_latency_s']}s | Min: {summary['min_latency_s']}s | Max: {summary['max_latency_s']}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run latency benchmark against a model serving endpoint")
    parser.add_argument("--endpoint", required=True, help="Base URL of the serving endpoint (e.g. http://vllm:8000 or http://litellm:4000)")
    parser.add_argument("--model-name", required=True, help="Model name to benchmark")
    parser.add_argument("--num-requests", type=int, default=10, help="Number of requests to send")
    parser.add_argument("--prompt", default="Hello, how are you?", help="Prompt to send")
    parser.add_argument("--api-key", default=None, help="Optional bearer token for OpenAI-compatible gateways")
    args = parser.parse_args()

    run_benchmark(args.endpoint, args.model_name, args.num_requests, args.prompt, args.api_key)
