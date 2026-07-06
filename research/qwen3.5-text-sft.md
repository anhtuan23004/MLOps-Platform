# Qwen3.5 Text-only SFT dưới 9B

Ngày nghiên cứu: 2026-07-06

Trạng thái: đề xuất nghiên cứu; chưa chọn story triển khai; chưa có GPU proof

## Kết luận

Trong riêng dòng Qwen3.5, chọn `Qwen/Qwen3.5-4B` post-trained làm ứng viên chính và
`Qwen/Qwen3.5-2B` làm baseline chi phí thấp. Dùng `Qwen3.5-0.8B` cho smoke test
pipeline, không dùng làm ứng viên chất lượng mặc định.

So sánh với Qwen2.5 và Qwen3 nằm tại
[Qwen text model comparison](qwen-text-model-comparison.md); ở cấp toàn họ model,
Qwen3.5-4B là challenger chứ chưa phải lựa chọn mặc định.

Một đề thi khác cố định `Qwen/Qwen3.5-2B` và chấm inference serving được tách tại
[Qwen3.5-2B inference serving challenge](qwen3.5-2b-inference-serving-challenge.md).
Đó không phải bài toán chọn model hoặc SFT.

Không chọn `Qwen/Qwen3.5-9B`. Tuy tên model ghi 9B tham số language model,
[collection chính thức của Qwen](https://huggingface.co/collections/Qwen/qwen35)
hiển thị artifact đầy đủ khoảng 10B vì Qwen3.5 còn có vision encoder. Với luật
`< 9B` tính trên toàn model, 9B không đạt; ngay cả khi luật chỉ tính language
backbone, dấu `<` vẫn loại đúng 9B.

Giai đoạn đầu chỉ SFT text. Không đưa image/video vào dataset, không cập nhật
vision encoder, và khi serve dùng chế độ text-only để bỏ vision profiling. Tuy
vậy, Qwen3.5 không có checkpoint text-only tách riêng: đây vẫn là native VLM với
đường thực thi text-only.

## Phạm vi

Mục tiêu là fine-tune model để đọc hồ sơ y khoa tiếng Việt dạng text và sinh
đúng JSON array ba trường `text`, `type`, `assertions` theo
[`docs/product/medical-concept-retrieval.md`](../docs/product/medical-concept-retrieval.md).

Trong phạm vi:

- Qwen3.5 dense dưới 9B tổng tham số.
- Text-only supervised fine-tuning bằng LoRA.
- Conversation JSONL hiện có.
- Structured extraction, không sinh chain-of-thought.
- Đánh giá chất lượng, tính hợp lệ và chi phí runtime.

Ngoài phạm vi:

- Fine-tune ảnh, video, OCR hoặc vision encoder.
- Hosted inference API.
- Full fine-tuning, GRPO/DPO hoặc distillation ở vòng đầu.
- Thay đổi production code trong nghiên cứu này.

## Các checkpoint hợp lệ

Qwen phát hành bốn dense small checkpoints. Con số ở cột "artifact đầy đủ" là
nhãn tổng tham số do Hugging Face hiển thị trong collection, gồm cả vision
encoder; đây là con số thận trọng để xét luật thi.

| Checkpoint post-trained | Language model | Artifact đầy đủ | Quyết định | Vai trò |
| --- | ---: | ---: | --- | --- |
| `Qwen/Qwen3.5-0.8B` | 0.8B | khoảng 0.9B | hợp lệ | smoke test, kiểm tra data/trainer |
| `Qwen/Qwen3.5-2B` | 2B | khoảng 2B | hợp lệ | baseline tốc độ/chi phí |
| `Qwen/Qwen3.5-4B` | 4B | khoảng 5B | hợp lệ, khuyến nghị | ứng viên SFT chính |
| `Qwen/Qwen3.5-9B` | 9B | khoảng 10B | loại | vượt giới hạn `< 9B` |

Ưu tiên checkpoint post-trained, không dùng biến thể `-Base` ở thí nghiệm đầu.
Post-trained model đã có instruction following và chat template; `-Base` chỉ
hợp lý nếu sau này có mục tiêu continued pretraining riêng với corpus y khoa đủ
lớn và phép đánh giá chống catastrophic forgetting.

## Đặc điểm ảnh hưởng đến SFT text

Theo [model card Qwen3.5-2B](https://huggingface.co/Qwen/Qwen3.5-2B) và
[Transformers Qwen3.5 documentation](https://huggingface.co/docs/transformers/model_doc/qwen3_5):

- Qwen3.5 là causal language model có vision encoder, được pretrain bằng text,
  image và video interleaved.
- Language backbone dùng hybrid stack: ba Gated DeltaNet layer cho mỗi một full
  attention layer.
- Context native là 262,144 token, nhưng đó không phải lý do để train ở context
  tối đa. Context train phải chọn theo phân phối dữ liệu và VRAM thực tế.
- Dòng small hỗ trợ non-thinking và thinking. Extraction phải dùng non-thinking
  deterministic; model card ghi không hỗ trợ soft switch `/think`/`/nothink`
  kiểu Qwen3.
- Qwen công bố hỗ trợ 201 ngôn ngữ và phương ngữ. Điều này làm model phù hợp để
  thử tiếng Việt, nhưng không thay thế benchmark y khoa tiếng Việt.

Khi inference text-only, model card cung cấp cờ vLLM `--language-model-only` để
bỏ vision encoder và multimodal profiling, giải phóng bộ nhớ cho KV cache.

## Phương án huấn luyện

### Framework

Dùng Unsloth vì repository đã có training container và runner. Tuy nhiên phải
pin một image digest/version đã xác minh; `latest` không đáp ứng reproducibility.

[Unsloth Qwen3.5 fine-tuning guide](https://unsloth.ai/docs/models/qwen3.5/fine-tune)
yêu cầu Transformers v5 cho Qwen3.5 và khuyến nghị BF16 LoRA. Guide cảnh báo
không dùng QLoRA 4-bit cho cả dense và MoE Qwen3.5 do sai lệch quantization cao.
Điều này xung đột trực tiếp với trainer hiện tại đang đặt `load_in_4bit=True`.

### Cấu hình khởi đầu

Đây là cấu hình thí nghiệm, không phải hyperparameter đã được chứng minh:

| Tham số | Giá trị khởi đầu | Lý do |
| --- | --- | --- |
| Model | `Qwen/Qwen3.5-4B` | lớn nhất còn khoảng cách an toàn dưới 9B |
| Precision | BF16 | đường được Unsloth khuyến nghị; tránh QLoRA |
| Adapter | LoRA | ít VRAM và artifact nhỏ hơn full fine-tune |
| Vision layers | frozen/excluded | dataset vòng đầu chỉ có text |
| LoRA rank/alpha | `r=16`, `alpha=16` | baseline nhỏ; chỉ tăng khi underfit có bằng chứng |
| LoRA dropout | `0` | baseline Unsloth; điều chỉnh sau bằng validation |
| Target modules | attention + MLP của language backbone | không cập nhật vision path |
| Sequence length | bắt đầu 4,096 | đủ chỗ cho system prompt, hồ sơ và JSON target; xác nhận bằng token profiling |
| Micro batch | 1 | giảm OOM; tăng effective batch bằng accumulation |
| Gradient accumulation | 8 | effective batch khởi đầu là 8 sequences/GPU |
| Learning rate | thử `5e-5`, `1e-4`, `2e-4` | chọn bằng validation, không chọn bằng train loss |
| Epochs | tối đa 3, early stop theo metric | synthetic data dễ overfit format |
| Scheduler | cosine, warmup ratio 0.03 | baseline ổn định để so sánh |
| Loss mask | assistant response only | không học lại system/user prompt |
| Packing | tắt ở baseline | dễ kiểm tra biên sample và truncation trước khi tối ưu throughput |
| Seed | `3407` và ít nhất 2 seed xác nhận | tránh chọn model từ một run may mắn |

Unsloth công bố mức dùng VRAM BF16 LoRA tham khảo là khoảng 3GB cho 0.8B, 5GB
cho 2B và 10GB cho 4B. Đây không phải capacity guarantee: sequence length,
activation, optimizer, batch và kernel cache làm số thực tế tăng. Với 4B ở
4,096 token nên bắt đầu trên GPU tối thiểu 16GB và ghi peak VRAM của run thật.

### Ma trận thí nghiệm tối thiểu

| Run | Model | Mục tiêu |
| --- | --- | --- |
| B0 | 0.8B, không SFT | smoke test prompt, parser và latency |
| B1 | 2B, không SFT | zero/few-shot baseline |
| B2 | 4B, không SFT | xác định lợi ích riêng của model size |
| S1 | 2B, BF16 LoRA | baseline SFT rẻ |
| S2 | 4B, BF16 LoRA | ứng viên chính |
| S3 | 4B, BF16 LoRA, seed khác | kiểm tra độ ổn định |

Chỉ mở rộng rank, context hoặc data khi error analysis chỉ ra bottleneck. Không
chạy grid lớn trước khi có frozen gold set.

## Data contract text-only

Giữ conversation JSONL đang được
[`llm_local/pipeline/dataset.py`](../llm_local/pipeline/dataset.py) kiểm tra:

```json
{
  "messages": [
    {"role": "system", "content": "<medical extraction system prompt>"},
    {"role": "user", "content": "Bệnh nhân không ho, tiền sử tăng huyết áp."},
    {"role": "assistant", "content": "[{\"text\":\"ho\",\"type\":\"TRIỆU_CHỨNG\",\"assertions\":[\"isNegated\"]},{\"text\":\"tăng huyết áp\",\"type\":\"CHẨN_ĐOÁN\",\"assertions\":[\"isHistorical\"]}]"}
  ]
}
```

Quy tắc dữ liệu:

- Assistant content chỉ chứa compact JSON array, không Markdown và không lời giải.
- `text` phải copy nguyên văn; không normalize spelling trong target.
- System prompt và chat template lúc train/inference phải giống nhau.
- Split theo source/scenario family trước khi tạo biến thể để chặn leakage.
- Profile token length sau khi áp chat template, không ước lượng từ số ký tự.
- Reject hoặc chunk có chủ đích; không truncate âm thầm vì có thể mất target entity.
- Gold test không được teacher-label và không dùng trong model selection lặp lại.

## Khoảng cách với pipeline hiện tại

Nghiên cứu code hiện tại cho thấy Qwen3.5 chưa thể thay model name rồi chạy:

| Hiện trạng | Tác động | Thay đổi cần có ở story triển khai |
| --- | --- | --- |
| `FastLanguageModel` + `load_in_4bit=True` | trái khuyến nghị BF16 LoRA Qwen3.5 | loader Qwen3.5 được support, BF16, không QLoRA |
| LoRA target modules hard-code theo transformer thường | có thể bỏ sót/sai với hybrid DeltaNet | lấy module map từ loader được support và kiểm tra trainable parameters |
| `max_steps=max(10, epochs*10)` | không phản ánh số row hoặc epochs khai báo | tính steps từ dataloader hoặc dùng `num_train_epochs` |
| Không cấu hình assistant-only loss rõ ràng | model có thể học system/user tokens | response-only masking và test label mask |
| Chỉ ghi train loss | không chứng minh extraction tốt hơn | chạy frozen validation metrics và lưu prediction artifacts |
| `max_seq_length=2048` | có nguy cơ thiếu chỗ cho hồ sơ dài + output | token profile rồi chọn 4,096/8,192 bằng evidence |
| Unsloth image mặc định `latest` | run không tái lập được | pin immutable tag/digest và dependency lock |
| Inference dùng loader text model cũ | chưa chứng minh load được Qwen3.5 adapter | dùng loader Qwen3.5 và test clean-host inference |
| Serve chưa bật text-only Qwen3.5 | vision profiling tốn bộ nhớ không cần thiết | xác minh runtime hỗ trợ `--language-model-only` |

Dataset schema hiện tại vẫn phù hợp cho text-only nên chưa cần mở rộng sang
multimodal `content` arrays.

## Evaluation và quality gates

Train loss chỉ là tín hiệu debug. Model được chọn theo frozen labeled set với
các metric sau:

1. JSON parse rate và exact three-field schema rate.
2. Tỷ lệ `text` xuất hiện nguyên văn trong source.
3. Exact-span micro/macro F1 và F1 theo từng entity type.
4. Assertion precision/recall/F1 cho `isNegated`, `isFamily`, `isHistorical`.
5. Exact document match và entity count error.
6. Metric theo document-length bins và theo scenario family.
7. Latency p50/p95, throughput, peak VRAM và artifact size.

Quality gates đề xuất trước khi chọn S2:

- 100% prediction files parse được và đúng schema.
- 100% emitted `text` tồn tại nguyên văn trong source, hoặc run bị loại.
- Không regression so với B2 ở bất kỳ entity type hiếm nào mà không có giải trình.
- S2 phải cải thiện gold metric so với cả B2 và S1; loss thấp hơn không đủ.
- Chạy lại seed xác nhận trước khi promote artifact.
- Public test chỉ dùng để kiểm tra coverage/structure, không báo cáo F1 giả.

## Rủi ro

- **Luật đếm tham số:** phải xin organizer xác nhận họ tính toàn checkpoint hay
  language backbone. Khuyến nghị 4B vẫn an toàn theo cả hai cách.
- **Native VLM:** dù train text-only, reproducibility bundle vẫn chứa vision
  encoder trừ khi có phương án export text backbone được organizer chấp nhận.
- **Framework mới:** Qwen3.5 cần Transformers v5 và kernel mới; phải pin commit/image
  sau GPU proof, không dựa vào `latest` hoặc nightly vô thời hạn.
- **Quantization:** QLoRA tiết kiệm VRAM nhưng hiện bị Unsloth khuyến cáo tránh;
  không đánh đổi chất lượng trước khi có A/B proof.
- **Structured generation:** JSON hợp lệ không đảm bảo entity đúng hoặc copy
  nguyên văn; deterministic validator vẫn bắt buộc.
- **Tiếng Việt y khoa:** benchmark tổng quát 201 ngôn ngữ không chứng minh domain
  accuracy. Gold set tiếng Việt là hard gate.

## Quyết định cần chốt trước implementation

1. Organizer xác nhận giới hạn tham số tính toàn model hay language backbone.
2. GPU mục tiêu và VRAM khả dụng cho 4B BF16 LoRA.
3. Frozen gold set, metric chính và ngưỡng chấp nhận.
4. Unsloth image digest/Transformers v5 version đã chạy thành công với Qwen3.5.
5. Có giữ vision weights trong submission bundle khi chỉ serve text hay không.

## Nguồn chính thức

- [Qwen3.5 official collection](https://huggingface.co/collections/Qwen/qwen35)
- [Qwen3.5-0.8B model card](https://huggingface.co/Qwen/Qwen3.5-0.8B)
- [Qwen3.5-2B model card](https://huggingface.co/Qwen/Qwen3.5-2B)
- [Qwen3.5-4B model card](https://huggingface.co/Qwen/Qwen3.5-4B)
- [Transformers Qwen3.5 documentation](https://huggingface.co/docs/transformers/model_doc/qwen3_5)
- [Unsloth Qwen3.5 fine-tuning guide](https://unsloth.ai/docs/models/qwen3.5/fine-tune)
- [TRL SFTTrainer documentation](https://huggingface.co/docs/trl/sft_trainer)
