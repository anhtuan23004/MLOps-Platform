# Qwen3 Text-only SFT dưới 9B

Ngày nghiên cứu: 2026-07-06

Trạng thái: đề xuất nghiên cứu; chưa có GPU proof

## Kết luận

Trong dòng Qwen3 text-only, chọn hai checkpoint để benchmark:

- `Qwen/Qwen3-8B` (8.2B): ứng viên chất lượng cao nhất còn dưới giới hạn 9B.
- `Qwen/Qwen3-4B-Instruct-2507` (4.0B): ứng viên chính khi ưu tiên VRAM,
  throughput và structured output không có reasoning block.

`Qwen3-0.6B` chỉ dùng smoke test; `Qwen3-1.7B` là baseline nhỏ. Không cần chạy
`Qwen3-4B` bản hybrid-thinking cũ nếu đã benchmark bản `Instruct-2507`, trừ khi
cần đo riêng giá trị của thinking mode.

So sánh toàn bộ họ Qwen nằm tại
[Qwen text model comparison](qwen-text-model-comparison.md).

## Checkpoint shortlist

| Checkpoint | Tham số chính thức | Context chính thức | Chế độ | Vai trò |
| --- | ---: | ---: | --- | --- |
| `Qwen/Qwen3-0.6B` | 0.6B | 32,768 | thinking + non-thinking | smoke test |
| `Qwen/Qwen3-1.7B` | 1.7B | 32,768 | thinking + non-thinking | low-cost baseline |
| `Qwen/Qwen3-4B-Instruct-2507` | 4.0B | 262,144 | non-thinking only | ứng viên 4B chính |
| `Qwen/Qwen3-8B` | 8.2B | 32,768; 131,072 với YaRN | thinking + non-thinking | ứng viên chất lượng chính |

Các model đều là causal text language model và Apache-2.0. Qwen3-8B ở 8.2B
nên đạt điều kiện `<9B` theo số tham số công bố, nhưng release packet vẫn phải
ghi chính xác checkpoint revision và parameter count.

## Vì sao Qwen3 phù hợp

Theo [Qwen3 official blog](https://qwenlm.github.io/blog/qwen3/), Qwen3 được
pretrain trên khoảng 36 nghìn tỷ token và hỗ trợ 119 ngôn ngữ/phương ngữ, có
tiếng Việt. Con số này rộng hơn Qwen2.5, nhưng không chứng minh accuracy y khoa.

Ưu điểm cho medical concept extraction:

- Pure text model: không mang vision encoder không dùng đến.
- Model 8.2B tận dụng gần hết giới hạn 9B.
- Chat template hỗ trợ hard switch `enable_thinking=False`.
- Qwen3-4B-Instruct-2507 chỉ non-thinking, tránh `<think>` làm hỏng JSON.
- Context native vượt xa nhu cầu hiện tại; có thể train ở 4,096 hoặc 8,192 để
  tiết kiệm VRAM.
- Có support chính thức trong Transformers, vLLM và Unsloth.

Rủi ro:

- Qwen3-8B bật thinking mặc định nếu không truyền đúng chat-template option.
- Direct-answer SFT có thể làm giảm reasoning capability; điều này chấp nhận được
  cho extractor chuyên biệt nhưng phải ghi rõ phạm vi artifact.
- Model card cảnh báo greedy decoding trong thinking mode có thể gây repetition.
  Pipeline này phải tắt thinking; structured inference vẫn cần termination test.
- Bản 2507 có báo cáo issue công khai về structured-output termination trên một
  số cấu hình vLLM. Đây chưa phải kết luận model lỗi, nhưng là regression case
  bắt buộc trước khi chọn runtime.

## Chế độ reasoning

Task chỉ cần compact JSON, không cần chain-of-thought. Với `Qwen3-8B`:

```python
tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True,
    enable_thinking=False,
)
```

Phải áp cùng chế độ khi render training rows và inference. Không dùng `/think`
hoặc `/no_think` nhúng trong clinical input vì đó là dữ liệu người dùng, không
phải control plane đáng tin cậy.

Với `Qwen3-4B-Instruct-2507`, không cần `enable_thinking=False`; model card ghi
checkpoint chỉ hỗ trợ non-thinking và không sinh `<think></think>`.

## SFT recipe đề xuất

Unsloth hỗ trợ Qwen3 LoRA/QLoRA và cung cấp 4-bit checkpoints. Khác Qwen3.5,
tài liệu Unsloth không đưa ra cảnh báo tránh QLoRA cho Qwen3 dense.

| Tham số | Baseline 4B | Baseline 8B |
| --- | --- | --- |
| Checkpoint | `Qwen3-4B-Instruct-2507` | `Qwen3-8B` |
| Method | QLoRA 4-bit, sau đó A/B BF16 LoRA nếu đủ VRAM | QLoRA 4-bit |
| Context train | 4,096 | 4,096 |
| LoRA | `r=16`, `alpha=16`, dropout `0` | giống 4B |
| Target | language attention + MLP linear modules | giống 4B |
| Micro batch | 1 | 1 |
| Gradient accumulation | 8 | 8 |
| Epochs | tối đa 3 | tối đa 3 |
| Learning-rate sweep | `5e-5`, `1e-4`, `2e-4` | `5e-5`, `1e-4` |
| Loss | assistant response only | assistant response only |
| Thinking | không hỗ trợ | hard-disable |

Đây là điểm bắt đầu thí nghiệm. Chỉ tăng context sau token profiling. Theo bảng
VRAM tối thiểu của Unsloth, QLoRA 8B cần khoảng 6GB và LoRA 16-bit khoảng 22GB;
activation/context làm nhu cầu thực tế cao hơn, nên phải đo peak VRAM trên host.

## Compatibility với repository

Conversation JSONL hiện tại phù hợp. Các thay đổi implementation vẫn cần story:

1. Pin `transformers>=4.51.0` hoặc image digest đã chứng minh Qwen3 hoạt động.
2. Dùng loader Unsloth hiện hành được tài liệu hỗ trợ và kiểm tra danh sách
   trainable modules; không giả định hard-coded target list là đầy đủ.
3. Render chat template với non-thinking nhất quán.
4. Thay fixed `max_steps` bằng epochs/steps dựa trên dataset.
5. Bật assistant-only loss và test label mask.
6. Pin Unsloth/vLLM image, model revision và adapter base-model reference.
7. Test EOS/termination, JSON parse và exact source text trên clean runtime.

## Thí nghiệm bắt buộc

| Run | Model | Precision | Mục đích |
| --- | --- | --- | --- |
| Q3-B0 | Qwen3-1.7B | 4-bit inference | baseline nhỏ |
| Q3-B1 | Qwen3-4B-Instruct-2507 | BF16/4-bit inference | pre-SFT baseline |
| Q3-S1 | Qwen3-4B-Instruct-2507 | QLoRA | ứng viên hiệu quả |
| Q3-B2 | Qwen3-8B | 4-bit inference | pre-SFT baseline |
| Q3-S2 | Qwen3-8B | QLoRA | ứng viên chất lượng |
| Q3-S3 | winner | cùng config, seed khác | xác nhận ổn định |

Không chọn winner theo benchmark tổng quát hoặc train loss. Dùng frozen gold
set với exact-span F1, type F1, assertion F1, invalid JSON rate, verbatim rate,
latency và peak VRAM.

## Nguồn chính thức

- [Qwen3 official blog](https://qwenlm.github.io/blog/qwen3/)
- [Qwen3 official collection](https://huggingface.co/collections/Qwen/qwen3)
- [Qwen3-8B model card](https://huggingface.co/Qwen/Qwen3-8B)
- [Qwen3-4B-Instruct-2507 model card](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507)
- [Qwen3 official repository](https://github.com/QwenLM/Qwen3)
- [Unsloth Qwen3 fine-tuning guide](https://unsloth.ai/docs/models/qwen3-how-to-run-and-fine-tune)
- [Unsloth VRAM requirements](https://unsloth.ai/docs/get-started/fine-tuning-for-beginners/unsloth-requirements)
- [Qwen3 structured-output termination report](https://github.com/QwenLM/Qwen3/issues/1700)
