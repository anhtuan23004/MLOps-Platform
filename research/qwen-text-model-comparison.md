# So sánh Qwen2.5, Qwen3 và Qwen3.5 cho text-only SFT

Ngày nghiên cứu: 2026-07-06

Trạng thái: decision support; chưa có benchmark y khoa hoặc GPU proof

> Tài liệu này phục vụ lựa chọn model cho SFT y khoa. Phase 1 cố định
> `Qwen/Qwen3.5-2B` và chấm inference serving là một track riêng; xem
> [Qwen3.5-2B inference serving challenge](qwen3.5-2b-inference-serving-challenge.md).

## Quyết định đề xuất

Không chọn một model chỉ từ model card. Chạy ba ứng viên chính trên cùng frozen
gold set:

1. `Qwen/Qwen3-8B` — ứng viên max-quality, 8.2B, pure text.
2. `Qwen/Qwen3-4B-Instruct-2507` — ứng viên efficiency, 4B, non-thinking only.
3. `Qwen/Qwen2.5-7B-Instruct` — control ổn định, 7.61B, explicit JSON strength.

Giữ `Qwen/Qwen3.5-4B` ở vòng challenger sau khi pipeline BF16 LoRA/
Transformers v5 chạy ổn định. Nếu GPU chỉ có 16GB, ưu tiên Qwen3-4B-Instruct-2507
QLoRA trước Qwen3.5-4B BF16 LoRA.

Nếu chỉ được chạy một thí nghiệm đầu tiên, chọn
`Qwen/Qwen3-4B-Instruct-2507`: model thuần text, không thinking block, Apache-2.0,
4B và có đủ headroom cho pipeline validation. Nếu cần model submission mạnh
nhất và compute cho phép, benchmark `Qwen3-8B` ngay sau đó.

## Phạm vi so sánh

- Task: Vietnamese medical concept extraction.
- Output: compact JSON array với `text`, `type`, `assertions`.
- Model tự host, tổng tham số `<9B`.
- Text-only SFT; không train vision.
- Adapter training, ưu tiên Unsloth + TRL + vLLM hiện có.

## So sánh family

| Tiêu chí | Qwen2.5 | Qwen3 | Qwen3.5 |
| --- | --- | --- | --- |
| Kiến trúc | pure text dense Transformer | pure text dense Transformer | unified VLM, hybrid DeltaNet/attention |
| Small models hợp lệ | 0.5B, 1.5B, 3B, 7B | 0.6B, 1.7B, 4B, 8.2B | 0.8B, 2B, 4B LM; full 4B artifact khoảng 5B |
| Model lớn nhất `<9B` | 7.61B | 8.2B | 4B LM / khoảng 5B full |
| Ngôn ngữ công bố | hơn 29, có tiếng Việt | 119, có tiếng Việt | 201 ngôn ngữ/phương ngữ |
| Pretraining scale công bố | tới 18T token | khoảng 36T token | không dùng làm proxy trực tiếp cho task |
| Structured JSON | model card nêu explicit improvement | instruction-following mạnh; phải benchmark JSON | phải benchmark JSON và text-only path |
| Thinking | không | hybrid; hard-disable được | thinking/non-thinking, control khác Qwen3 |
| Best extraction checkpoint | 7B-Instruct | 4B-Instruct-2507 hoặc 8B | 4B post-trained |
| Fine-tune baseline | QLoRA 4-bit | QLoRA 4-bit | BF16 LoRA; tránh QLoRA theo Unsloth |
| Transformers floor | 4.37.0 | 4.51.0 | v5 theo Unsloth guide |
| Runtime maturity | cao nhất | cao | mới hơn; cần text-only runtime validation |
| Vision overhead | không | không | có trong full checkpoint |
| License | Apache trừ 3B/72B | Apache-2.0 | Apache-2.0 cho shortlisted checkpoints |

Số ngôn ngữ, token pretraining và general benchmark không phải metric chọn model.
Chúng chỉ giải thích prior trước khi chạy gold evaluation.

## So sánh checkpoint chính

| Checkpoint | Params tính eligibility | Method đầu tiên | Ưu điểm | Nhược điểm | Vai trò |
| --- | ---: | --- | --- | --- | --- |
| Qwen2.5-1.5B-Instruct | 1.54B | QLoRA | rẻ, runtime trưởng thành | capacity thấp | smoke/baseline |
| Qwen2.5-7B-Instruct | 7.61B | QLoRA | explicit JSON, stable stack | cũ hơn, 29+ languages | control chính |
| Qwen3-1.7B | 1.7B | QLoRA | multilingual mới hơn | capacity thấp, thinking control | small baseline |
| Qwen3-4B-Instruct-2507 | 4.0B | QLoRA | pure text, non-thinking, 256K native | structured termination cần regression test | first practical candidate |
| Qwen3-8B | 8.2B | QLoRA | gần max budget, 119 languages | VRAM/latency cao, phải hard-disable thinking | max-quality candidate |
| Qwen3.5-2B | khoảng 2B full | BF16 LoRA | newest small baseline | new stack, vision baggage | Qwen3.5 baseline |
| Qwen3.5-4B | khoảng 5B full | BF16 LoRA | newer multilingual model | vision overhead, Transformers v5, no QLoRA recommendation | challenger |

Không đưa Qwen2.5-3B vào shortlist do license khác Apache. Không đưa Qwen3.5-9B
vì official collection hiển thị full artifact khoảng 10B và nominal LM đúng 9B
cũng không đạt điều kiện `<9B`.

## Chấm điểm trước benchmark

Đây là readiness score, không phải quality score.

| Model | Eligibility | Pipeline fit | Repro maturity | Compute efficiency | Tổng quan |
| --- | ---: | ---: | ---: | ---: | --- |
| Qwen2.5-7B-Instruct | 5/5 | 5/5 | 5/5 | 3/5 | control ít rủi ro nhất |
| Qwen3-4B-Instruct-2507 | 5/5 | 4/5 | 4/5 | 5/5 | lựa chọn triển khai đầu tiên |
| Qwen3-8B | 5/5 | 4/5 | 4/5 | 2/5 | ứng viên chất lượng cao |
| Qwen3.5-4B | 5/5 | 2/5 | 2/5 | 3/5 | challenger sau khi nâng stack |

Không chấm "quality" vì chưa có labeled Vietnamese medical benchmark. Bất kỳ
xếp hạng chất lượng nào ở thời điểm này đều là suy đoán.

## Cùng một experimental protocol

### Data

- Cùng train/validation/test split và dataset digest.
- Cùng compact assistant JSON; không chain-of-thought.
- Cùng system prompt semantics.
- Split theo source/scenario trước augmentation.
- Token profile riêng theo tokenizer; cùng truncation policy, không nhất thiết
  cùng token count nếu tokenizer khác.

### Training

- Context khởi đầu 4,096.
- Effective batch 8 sequences.
- LoRA `r=16`, `alpha=16`, dropout `0` làm common baseline.
- Assistant-only loss.
- Tối đa 3 epochs, validation theo fixed intervals.
- QLoRA cho Qwen2.5/Qwen3; BF16 LoRA cho Qwen3.5.
- Ít nhất hai seed cho winner.

Việc dùng precision khác nhau là có chủ đích vì Qwen3.5 QLoRA hiện bị Unsloth
khuyến cáo tránh. Báo cáo phải tách model quality khỏi training cost.

### Inference

- Non-thinking cho mọi model.
- Temperature 0/do-sample false là structural baseline; nếu Qwen model card
  cảnh báo greedy cho một chế độ, chỉ áp cảnh báo đó cho thinking mode, vốn bị tắt.
- Cùng max input/output budget.
- Không retry để che invalid output trong raw model comparison.
- Sau raw comparison mới đo validator/retry production policy.

### Metrics

Quality:

- JSON parse rate và exact three-field schema rate.
- Exact-span micro/macro F1.
- F1 theo năm entity types.
- Assertion precision/recall/F1.
- Verbatim-copy rate.
- Exact document match và entity count error.
- Metrics theo document length/scenario bins.

Operations:

- Train wall time, peak VRAM và tokens/second.
- Adapter size và merged artifact size.
- Inference latency p50/p95, throughput và peak VRAM.
- Cold-start time và clean-host reproducibility.

## Decision gates

1. Loại model nếu full parameter count không chứng minh được `<9B`.
2. Loại run nếu JSON/schema hoặc verbatim-copy rate dưới 100% sau deterministic
   validation; raw rate vẫn được lưu cho error analysis.
3. Không chọn model chỉ vì loss thấp hơn.
4. Winner phải cải thiện primary gold metric qua ít nhất hai seed.
5. Nếu quality chênh nhỏ hơn agreed tolerance, chọn model có p95 latency/VRAM thấp hơn.
6. Qwen3.5 chỉ promote khi pinned Transformers v5/Unsloth/vLLM stack chạy clean-host.
7. Qwen3-2507 phải qua termination regression ở raw generation và structured API.

## Khuyến nghị theo GPU

| GPU VRAM | Thứ tự thử |
| ---: | --- |
| 8-12GB | Qwen2.5-1.5B smoke → Qwen3-4B-Instruct-2507 QLoRA |
| 16GB | Qwen3-4B-Instruct-2507 QLoRA → Qwen2.5-7B QLoRA → Qwen3-8B QLoRA |
| 24GB+ | thêm Qwen3-8B 16-bit LoRA A/B; Qwen3.5-4B BF16 LoRA challenger |

Các mức này là kế hoạch thử, không phải guarantee. Unsloth công bố floor tổng
quát: QLoRA 7B khoảng 5GB, 8B khoảng 6GB; 16-bit LoRA tương ứng khoảng 19GB và
22GB. Context và activation cần thêm headroom.

## Tác động đến roadmap implementation

Một story implementation nên tách hai lane:

1. **Legacy-compatible lane:** Qwen2.5/Qwen3 QLoRA text-only, nâng trainer tối
   thiểu nhưng sửa schedule, response mask, validation và pinning.
2. **Qwen3.5 lane:** Transformers v5 + BF16 LoRA + text-only serving, chạy sau
   khi legacy lane tạo được baseline đáng tin.

Không mở rộng dataset schema sang multimodal ở cả hai lane.

## Tài liệu chi tiết

- [Qwen2.5 text-only SFT](qwen2.5-text-sft.md)
- [Qwen3 text-only SFT](qwen3-text-sft.md)
- [Qwen3.5 text-only SFT](qwen3.5-text-sft.md)

## Nguồn chính thức

- [Qwen2.5 official release](https://qwenlm.github.io/blog/qwen2.5/)
- [Qwen2.5-7B-Instruct model card](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct)
- [Qwen3 official blog](https://qwenlm.github.io/blog/qwen3/)
- [Qwen3-8B model card](https://huggingface.co/Qwen/Qwen3-8B)
- [Qwen3-4B-Instruct-2507 model card](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507)
- [Qwen3.5 official collection](https://huggingface.co/collections/Qwen/qwen35)
- [Unsloth Qwen3 guide](https://unsloth.ai/docs/models/qwen3-how-to-run-and-fine-tune)
- [Unsloth Qwen3.5 guide](https://unsloth.ai/docs/models/qwen3.5/fine-tune)
- [Unsloth VRAM requirements](https://unsloth.ai/docs/get-started/fine-tuning-for-beginners/unsloth-requirements)
