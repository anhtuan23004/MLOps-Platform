import argparse
import glob
import json

import matplotlib.pyplot as plt
import pandas as pd


def collect_metrics(results_dir, output_dir):
    files = sorted(glob.glob(f"{results_dir}/benchmark_*.json"))
    if not files:
        print("No benchmark results found.")
        return

    records = []
    for f in files:
        with open(f) as fh:
            data = json.load(fh)
            records.append({
                "model": data["model"],
                "timestamp": data["timestamp"],
                "avg_latency_s": data["avg_latency_s"],
                "min_latency_s": data["min_latency_s"],
                "max_latency_s": data["max_latency_s"],
                "num_requests": data["num_requests"],
                "successful": data["successful"],
            })

    df = pd.DataFrame(records)
    print(df.to_string(index=False))

    # Save summary CSV
    summary_path = f"{output_dir}/metrics_summary.csv"
    df.to_csv(summary_path, index=False)
    print(f"\nSummary saved to {summary_path}")

    # Generate latency chart
    plt.figure(figsize=(10, 5))
    for model in df["model"].unique():
        model_df = df[df["model"] == model]
        plt.plot(model_df["timestamp"], model_df["avg_latency_s"], marker="o", label=model)
    plt.xlabel("Timestamp")
    plt.ylabel("Avg Latency (s)")
    plt.title("Model Latency Over Time")
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    chart_path = f"{output_dir}/latency_chart.png"
    plt.savefig(chart_path)
    print(f"Chart saved to {chart_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collect and visualize benchmark metrics")
    parser.add_argument("--results-dir", default="/app/results", help="Directory containing benchmark JSON results")
    parser.add_argument("--output-dir", default="/app/dashboards", help="Directory to save reports and charts")
    args = parser.parse_args()

    collect_metrics(args.results_dir, args.output_dir)
