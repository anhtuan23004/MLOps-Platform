# Qwen2.5 Text-only SFT dưới 9B

Ngày nghiên cứu: 2026-07-06

Trạng thái: đề xuất nghiên cứu; chưa có GPU proof

## Kết luận

Chọn `Qwen/Qwen2.5-7B-Instruct` (7.61B) làm control baseline ổn định. Model card
chính thức nêu rõ cải thiện về instruction following, structured data và JSON,
đúng với output contract của project.

Dùng `Qwen2.5-1.5B-Instruct` cho smoke/low-cost baseline. Không ưu tiên 3B vì
Qwen công bố 3B là ngoại lệ không dùng Apache-2.0; 4B Qwen3 mới hơn là đối thủ
gần kích thước và có license đơn giản hơn.

So sánh toàn bộ họ Qwen nằm tại
[Qwen text model comparison](qwen-text-model-comparison.md).

## Checkpoint shortlist

| Checkpoint | Tham số | Context model card | License | Vai trò |
| --- | ---: | ---: | --- | --- |
| `Qwen/Qwen2.5-0.5B-Instruct` | khoảng 0.5B | 32,768 | Apache-2.0 | smoke test rất nhỏ |
| `Qwen/Qwen2.5-1.5B-Instruct` | 1.54B | 32,768 | Apache-2.0 | low-cost baseline |
| `Qwen/Qwen2.5-3B-Instruct` | 3.09B | 32,768 | Qwen Research | không ưu tiên |
| `Qwen/Qwen2.5-7B-Instruct` | 7.61B | 131,072; generation 8,192 | Apache-2.0 | control baseline chính |

Tất cả đều dưới 9B. Không dùng Coder/Math variants vì domain adaptation đó
không trực tiếp phục vụ Vietnamese medical extraction và làm comparison khó
diễn giải.

## Vì sao vẫn cần Qwen2.5

Qwen2.5 cũ hơn nhưng có ba giá trị thực dụng:

- Pure text decoder, không có vision overhead.
- Model card nêu explicit improvement cho structured outputs, đặc biệt JSON.
- `transformers>=4.37.0` đã hỗ trợ; runtime và fine-tuning path trưởng thành hơn
  Qwen3.5.
- Không có thinking block, nên prompt/inference contract đơn giản.
- Hỗ trợ hơn 29 ngôn ngữ, model card liệt kê tiếng Việt.
- 7.61B dùng gần hết budget nhưng còn khoảng cách rõ với 9B.

Qwen2.5 không mặc nhiên tốt hơn các model mới. Nó là control giúp trả lời liệu
Qwen3/Qwen3.5 có thực sự cải thiện task metric hay chỉ tăng complexity.

## Context và structured output

Model card 7B ghi full context 131,072 và generation 8,192. Tuy nhiên config
mặc định dùng 32,768; context dài hơn cần YaRN và model card cảnh báo static YaRN
có thể ảnh hưởng short-text performance.

Project không cần YaRN ở vòng đầu. Public documents hiện dài tối đa 4,428 ký tự;
cần profile token sau chat template rồi chọn 4,096 hoặc 8,192. Dùng 131K chỉ làm
tăng KV/activation cost mà chưa có lợi ích được chứng minh.

## SFT recipe đề xuất

| Tham số | Baseline 1.5B | Baseline 7B |
| --- | --- | --- |
| Checkpoint | `Qwen2.5-1.5B-Instruct` | `Qwen2.5-7B-Instruct` |
| Method | QLoRA 4-bit | QLoRA 4-bit |
| Context train | 4,096 | 4,096 |
| LoRA | `r=16`, `alpha=16`, dropout `0` | giống 1.5B |
| Target | `q/k/v/o`, `gate/up/down` projections | giống 1.5B |
| Micro batch | 1-2 | 1 |
| Gradient accumulation | để effective batch = 8 | 8 |
| Epochs | tối đa 3 | tối đa 3 |
| Learning-rate sweep | `1e-4`, `2e-4` | `5e-5`, `1e-4` |
| Loss | assistant response only | assistant response only |
| Decoding eval | deterministic baseline | deterministic baseline |

Unsloth công bố mức tối thiểu tổng quát khoảng 5GB VRAM cho QLoRA 7B và 19GB
cho 16-bit LoRA 7B. Đây chỉ là floor; sequence length, batch và activation cần
headroom. Vì current trainer đã dùng 4-bit, Qwen2.5 là migration path ít thay đổi
nhất, nhưng vẫn chưa được GPU-proven trong repo.

## Compatibility với repository

Những phần có thể giữ:

- Conversation JSONL `messages` schema.
- `AutoModelForCausalLM`/tokenizer-style chat template.
- QLoRA 4-bit và projection target hiện tại về mặt kiến trúc.
- vLLM text serving path.

Những phần vẫn phải sửa trước run thật:

1. Pin model revision, Transformers/Unsloth image và CUDA runtime.
2. Bật assistant-only loss; hiện trainer không chứng minh label mask đúng.
3. Thay `max_steps=max(10, epochs*10)` bằng schedule theo dataset.
4. Load và đánh giá validation split, không chỉ train split.
5. Profile token length và fail thay vì truncate mất entity/target.
6. Log dataset digest, base model revision, adapter config và gold metrics.
7. Test exact same chat template/EOS khi inference và serving.

## License gate cho 3B

[Qwen2.5 official release](https://qwenlm.github.io/blog/qwen2.5/) ghi mọi model
open-source trừ 3B và 72B dùng Apache-2.0. Vì project cần reproducibility bundle
và có thể chịu luật thi riêng, 3B chỉ được đưa vào experiment nếu license review
xác nhận quyền dùng/phân phối. Không có lý do kỹ thuật đủ mạnh để nhận thêm gate
này khi Qwen3-4B-Instruct-2507 tồn tại.

## Thí nghiệm bắt buộc

| Run | Model | Mục đích |
| --- | --- | --- |
| Q25-B0 | 1.5B, không SFT | smoke + baseline nhỏ |
| Q25-S0 | 1.5B QLoRA | kiểm tra pipeline học được task |
| Q25-B1 | 7B, không SFT | zero/few-shot control |
| Q25-S1 | 7B QLoRA | control SFT chính |
| Q25-S2 | 7B QLoRA, seed khác | xác nhận nếu model vào shortlist |

Model được đánh giá trên cùng split, prompt, max input/output và decoding policy
với Qwen3/Qwen3.5.

## Nguồn chính thức

- [Qwen2.5 official release](https://qwenlm.github.io/blog/qwen2.5/)
- [Qwen2.5 official collection](https://huggingface.co/collections/Qwen/qwen25)
- [Qwen2.5-7B-Instruct model card](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct)
- [Qwen2.5-3B-Instruct model card](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct)
- [Qwen2.5-1.5B-Instruct model card](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct)
- [Unsloth VRAM requirements](https://unsloth.ai/docs/get-started/fine-tuning-for-beginners/unsloth-requirements)
