# Research

Thư mục này chứa các nghiên cứu kỹ thuật tách khỏi product contract và story
implementation. Kết luận trong đây là đầu vào cho quyết định; chúng không phải
bằng chứng rằng pipeline đã được triển khai hoặc chạy trên GPU.

## Model fine-tuning

- [Qwen text model comparison](qwen-text-model-comparison.md) — so sánh trực
  tiếp Qwen2.5, Qwen3 và Qwen3.5 dưới 9B, shortlist và protocol chọn model.
- [Qwen3 text-only SFT dưới 9B](qwen3-text-sft.md) — Qwen3-8B và
  Qwen3-4B-Instruct-2507, reasoning control và QLoRA plan.
- [Qwen3.5 text-only SFT dưới 9B](qwen3.5-text-sft.md) — lựa chọn checkpoint,
  phương án BF16 LoRA, data contract, đánh giá và khoảng cách với trainer hiện tại.
- [Qwen2.5 text-only SFT dưới 9B](qwen2.5-text-sft.md) — Qwen2.5-7B control,
  structured JSON, license và compatibility baseline.

## Inference serving

- [Qwen3.5-2B inference serving challenge](qwen3.5-2b-inference-serving-challenge.md)
  — phân tích trace 120 request và hướng tối ưu ERS/Accuracy Gate trên MIG H200
  18GB: 28K context, prefix caching, scheduler, MTP và FP8.
- [Peer-reviewed papers cho Qwen3.5 serving](qwen3.5-serving-optimization-papers.md)
  — phân tích paper peer-reviewed từ SOSP/OSDI/MLSys/ICML/NeurIPS/ICLR/ACL về
  PagedAttention, chunked prefill, shared-prefix, MTP, quantization và Hopper.
