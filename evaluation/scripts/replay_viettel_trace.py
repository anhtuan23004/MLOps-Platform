import argparse
import asyncio
import json
import time
import urllib.error
import urllib.request
from pathlib import Path


F_TTFT_MS = 100.0
C_TTFT_MS = 1500.0
F_TPOT_MS = 20.0
C_TPOT_MS = 45.0
GAMMA = 2.0
TTFT_WEIGHT = 0.5


def clamp(value, lower=0.0, upper=1.0):
    return max(lower, min(upper, value))


def score_request(ttft_ms, tpot_ms, output_tokens, error):
    if error or output_tokens <= 0 or ttft_ms is None or tpot_ms is None:
        return 0.0

    s_ttft = clamp((C_TTFT_MS - ttft_ms) / (C_TTFT_MS - F_TTFT_MS)) ** GAMMA
    s_tpot = clamp((C_TPOT_MS - tpot_ms) / (C_TPOT_MS - F_TPOT_MS)) ** GAMMA
    return TTFT_WEIGHT * s_ttft + (1.0 - TTFT_WEIGHT) * s_tpot


def load_trace(path):
    requests = []
    with Path(path).open() as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            item = json.loads(line)
            item["_line_number"] = line_number
            requests.append(item)
    return requests


def parse_sse_payload(raw_line):
    line = raw_line.decode("utf-8", errors="replace").strip()
    if not line or not line.startswith("data:"):
        return None
    data = line.removeprefix("data:").strip()
    if data == "[DONE]":
        return "[DONE]"
    return json.loads(data)


def post_json_stream(url, payload, timeout_s):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    started = time.perf_counter()
    first_token_at = None
    finished = None
    content_chunks = 0
    completion_tokens = None
    response_id = None

    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        status_code = resp.status
        for raw_line in resp:
            event = parse_sse_payload(raw_line)
            now = time.perf_counter()
            if event is None:
                continue
            if event == "[DONE]":
                finished = now
                break

            response_id = event.get("id", response_id)
            usage = event.get("usage")
            if usage and usage.get("completion_tokens") is not None:
                completion_tokens = int(usage["completion_tokens"])

            for choice in event.get("choices", []):
                delta = choice.get("delta") or {}
                content = delta.get("content")
                if content:
                    if first_token_at is None:
                        first_token_at = now
                    content_chunks += 1

    finished = finished or time.perf_counter()
    output_tokens = completion_tokens if completion_tokens is not None else content_chunks
    ttft_ms = (first_token_at - started) * 1000.0 if first_token_at else None
    if first_token_at and output_tokens > 1:
        tpot_ms = ((finished - first_token_at) * 1000.0) / (output_tokens - 1)
    elif first_token_at and output_tokens == 1:
        tpot_ms = 0.0
    else:
        tpot_ms = None

    return {
        "status_code": status_code,
        "response_id": response_id,
        "latency_ms": (finished - started) * 1000.0,
        "ttft_ms": ttft_ms,
        "tpot_ms": tpot_ms,
        "output_tokens": output_tokens,
        "token_count_source": "usage" if completion_tokens is not None else "stream_chunks",
        "error": None,
    }


def post_json_non_stream(url, payload, timeout_s):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    started = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        raw = resp.read()
        finished = time.perf_counter()
        data = json.loads(raw)

    usage = data.get("usage") or {}
    output_tokens = int(usage.get("completion_tokens") or 0)
    latency_ms = (finished - started) * 1000.0

    # Non-streaming cannot observe TTFT externally; these fields are conservative
    # latency proxies for smoke testing only.
    ttft_ms = latency_ms
    tpot_ms = latency_ms / output_tokens if output_tokens else None
    return {
        "status_code": resp.status,
        "response_id": data.get("id"),
        "latency_ms": latency_ms,
        "ttft_ms": ttft_ms,
        "tpot_ms": tpot_ms,
        "output_tokens": output_tokens,
        "token_count_source": "usage",
        "error": None,
    }


def send_one(endpoint, body, timeout_s, stream):
    url = endpoint.rstrip("/") + "/v1/chat/completions"
    try:
        if stream:
            return post_json_stream(url, body, timeout_s)
        return post_json_non_stream(url, body, timeout_s)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return {
            "status_code": exc.code,
            "latency_ms": None,
            "ttft_ms": None,
            "tpot_ms": None,
            "output_tokens": 0,
            "token_count_source": None,
            "error": detail[:1000],
        }
    except Exception as exc:
        return {
            "status_code": None,
            "latency_ms": None,
            "ttft_ms": None,
            "tpot_ms": None,
            "output_tokens": 0,
            "token_count_source": None,
            "error": repr(exc),
        }


async def replay_request(item, endpoint, model, timeout_s, stream, speed):
    await asyncio.sleep((item["timestamp_ms"] / 1000.0) / speed)

    body = dict(item["body"])
    if model:
        body["model"] = model
    if stream:
        body["stream"] = True
        body["stream_options"] = {"include_usage": True}

    scheduled_at = time.perf_counter()
    result = await asyncio.to_thread(send_one, endpoint, body, timeout_s, stream)
    finished_at = time.perf_counter()
    request_score = score_request(
        result.get("ttft_ms"),
        result.get("tpot_ms"),
        result.get("output_tokens", 0),
        result.get("error"),
    )

    return {
        "request_id": item.get("request_id"),
        "timestamp_ms": item.get("timestamp_ms"),
        "scheduled_latency_ms": (finished_at - scheduled_at) * 1000.0,
        "score": request_score,
        **result,
    }


def summarize(results):
    successes = [r for r in results if not r.get("error") and r.get("output_tokens", 0) > 0]
    ttfts = sorted(r["ttft_ms"] for r in successes if r.get("ttft_ms") is not None)
    tpots = sorted(r["tpot_ms"] for r in successes if r.get("tpot_ms") is not None)

    def percentile(values, p):
        if not values:
            return None
        index = min(len(values) - 1, round((len(values) - 1) * p))
        return values[index]

    return {
        "requests": len(results),
        "successful": len(successes),
        "failed": len(results) - len(successes),
        "ers": sum(r["score"] for r in results) / len(results) if results else 0.0,
        "ttft_ms": {
            "p50": percentile(ttfts, 0.50),
            "p90": percentile(ttfts, 0.90),
            "p95": percentile(ttfts, 0.95),
            "p99": percentile(ttfts, 0.99),
        },
        "tpot_ms": {
            "p50": percentile(tpots, 0.50),
            "p90": percentile(tpots, 0.90),
            "p95": percentile(tpots, 0.95),
            "p99": percentile(tpots, 0.99),
        },
    }


async def replay(args):
    trace = load_trace(args.trace)
    if args.limit:
        trace = trace[: args.limit]

    tasks = [
        asyncio.create_task(
            replay_request(
                item=item,
                endpoint=args.endpoint,
                model=args.model,
                timeout_s=args.timeout_s,
                stream=args.stream,
                speed=args.speed,
            )
        )
        for item in trace
    ]
    results = await asyncio.gather(*tasks)
    results.sort(key=lambda row: row["request_id"])

    report = {
        "trace": str(args.trace),
        "endpoint": args.endpoint,
        "model_override": args.model,
        "stream": args.stream,
        "speed": args.speed,
        "summary": summarize(results),
        "results": results,
    }
    print(json.dumps(report["summary"], indent=2))

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2))
        print(f"Saved report to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Replay Viettel AI Race trace against an OpenAI-compatible endpoint.")
    parser.add_argument("--trace", required=True, help="Path to trace-round1.jsonl")
    parser.add_argument("--endpoint", default="http://localhost:8000", help="Endpoint base URL")
    parser.add_argument("--model", default=None, help="Optional model name override")
    parser.add_argument("--output", default=None, help="Optional JSON report path")
    parser.add_argument("--timeout-s", type=float, default=600.0, help="Per-request timeout")
    parser.add_argument("--limit", type=int, default=None, help="Replay only the first N requests")
    parser.add_argument("--speed", type=float, default=1.0, help="Replay speed multiplier")
    parser.add_argument("--stream", action="store_true", help="Use streaming to measure TTFT/TPOT")
    args = parser.parse_args()

    if args.speed <= 0:
        raise SystemExit("--speed must be positive")

    asyncio.run(replay(args))


if __name__ == "__main__":
    main()
