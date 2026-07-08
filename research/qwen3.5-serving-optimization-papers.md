# Phân tích paper peer-reviewed cho tối ưu Qwen3.5-2B serving

Ngày nghiên cứu: 2026-07-06

## Phạm vi

Tài liệu này tổng hợp các paper có liên quan trực tiếp tới bài toán serving
`Qwen/Qwen3.5-2B` trên một MIG H200 18GB. Workload cụ thể đã được phân tích tại
[Qwen3.5-2B inference serving challenge](qwen3.5-2b-inference-serving-challenge.md):

- 6 burst, mỗi burst 20 request và cách nhau 5 giây.
- Input 12.9K–27.4K tokens, output cap 200 tokens.
- System prefix chung dài khoảng 6.4K tokens.
- 20 conversation lineages tái sử dụng prefix qua các burst.
- Prefix caching có upper bound giảm 82.3% số token cần prefill nếu cache không bị
  eviction.

Đây là workload long-prefill, short-output, bursty và prefix-heavy. Vì vậy không
thể lấy throughput headline từ paper rồi áp trực tiếp; ưu tiên phải là cache reuse,
prefill/decode interference và tail latency.

### Tiêu chí chọn nguồn

Trong Computer Science và Machine Learning, kết quả hệ thống mới thường được công
bố ở flagship conference proceedings thay vì journal truyền thống. Vì vậy “tạp chí
nổi tiếng” trong tài liệu này được hiểu là các venue peer-reviewed hàng đầu:

- Systems: SOSP, OSDI, MLSys.
- Machine Learning: ICML, NeurIPS, ICLR.
- NLP: ACL main conference.

Main analysis chỉ dùng paper đã xuất bản tại các venue trên. Preprint, technical
report và workshop chỉ được ghi ở cuối như nguồn phụ, không dùng để quyết định
profile.

## Kết luận

Thứ tự kỹ thuật theo mức phù hợp với trace:

1. **Automatic prefix caching và cache residency.** PagedAttention, Prompt Cache,
   RadixAttention và ChunkAttention đều củng cố shared prefix là cơ hội lớn nhất.
2. **Chunked prefill và iteration-level scheduling.** Orca và Sarathi-Serve giải
   thích trực tiếp trade-off giữa TTFT và TPOT của 20 long-prefill requests.
3. **KV-cache capacity.** FP8 KV đáng thử khi telemetry cho thấy eviction hoặc
   preemption; KIVI/KVQuant không chứng minh trực tiếp cấu hình FP8 của vLLM.
4. **Native MTP.** ICML 2024 chứng minh MTP/speculative heads có tiềm năng, nhưng
   đây vẫn chỉ là challenger vì output ngắn và prefix cache cần memory residency.
5. **Hopper attention kernels.** FlashAttention-3 có nền tảng phần cứng phù hợp,
   nhưng gain end-to-end sẽ nhỏ hơn kernel headline vì Qwen3.5 dùng hybrid
   Gated DeltaNet/full attention và benchmark chạy trên MIG.
6. **Disaggregated serving.** DistServe giải thích interference nhưng không triển
   khai được khi chỉ có một GPU partition.

## Ma trận paper

| Paper | Kỹ thuật chính | Mức phù hợp | Quyết định cho challenge |
| --- | --- | --- | --- |
| vLLM/PagedAttention, SOSP 2023 | Paged KV memory, sharing KV blocks | Rất cao | Giữ vLLM baseline; đo cache hit và eviction |
| Orca, OSDI 2022 | Iteration-level scheduling, continuous batching | Cao | Tune batch/concurrency; không request-level batch |
| Sarathi-Serve, OSDI 2024 | Chunked prefill, stall-free scheduling | Rất cao | Sweep token budget để cân bằng TTFT/TPOT |
| Prompt Cache, MLSys 2024 | Tái sử dụng attention state của prompt modules | Rất cao | Củng cố APC; không cần schema riêng cho fixed trace |
| SGLang, NeurIPS 2024 | RadixAttention cho prefix tree | Rất cao về workload | Alternate runtime sau khi vLLM plateau |
| ChunkAttention, ACL 2024 | Prefix-tree KV + shared-prefix attention kernel | Cao | R&D option sau khi APC plateau |
| Speculative Decoding, ICML 2023 | Draft-and-verify lossless decoding | Trung bình | Giải thích acceptance/speedup; không thêm draft model |
| Multi-token Prediction, ICML 2024 | Nhiều future-token heads | Cao cho native MTP | MTP-1 trước; không chuyển trực tiếp headline 3× |
| Medusa, ICML 2024 | Nhiều decoding heads, tree verification | Trung bình | Cơ sở cho native MTP; không dùng headline speedup |
| EAGLE, ICML 2024 | Feature-level speculative sampling | Thấp cho implementation | Không thêm draft architecture vào fixed model |
| KIVI, ICML 2024 | Asymmetric 2-bit KV quantization | Trung bình | Chứng minh KV memory là bottleneck; không dùng 2-bit ngay |
| KVQuant, NeurIPS 2024 | 3-bit/non-uniform KV quantization | Trung bình | Research path sau FP8; cần kernel và quality proof riêng |
| SmoothQuant, ICML 2023 | W8A8 post-training quantization | Trung bình | Chỉ thử sau BF16/FP8; GPQA bắt buộc |
| FlashAttention-3, NeurIPS 2024 | Hopper async pipeline và FP8 attention | Trung bình–cao | Kiểm tra backend/kernel thực tế của image BTC |
| Gated DeltaNet, ICLR 2025 | Linear recurrent state + delta rule | Kiến trúc nền | Không giả định mọi KV-cache result của Transformer chuyển nguyên vẹn |
| DistServe, OSDI 2024 | Tách prefill/decode qua nhiều GPU | Không triển khai | Chỉ dùng để định nghĩa interference metrics |

## 1. Scheduling và chunked prefill

### Orca: continuous batching là nền tảng

[Orca](https://www.usenix.org/conference/osdi22/presentation/yu) thay request-level
scheduling bằng iteration-level scheduling: batch có thể thay đổi sau mỗi model
iteration, request đã xong rời batch và request mới được nhận vào. Ý tưởng này là
nền tảng của continuous batching trong các runtime hiện đại.

Áp dụng cho trace:

- Không cần triển khai Orca; vLLM đã có continuous batching.
- Biến cần tune là admission: `max-num-seqs`, token budget và preemption.
- `max-num-seqs=20` khớp một burst nhưng không có headroom nếu burst trước chưa
  xong. `24` là starting point hợp lý; `20` và `32` là hai challenger.

Giới hạn chuyển giao: Orca đánh giá các Transformer lớn và distributed serving;
con số speedup của paper không phải dự báo cho Qwen3.5-2B trên MIG.

### Sarathi-Serve: paper phù hợp nhất với trace

[Sarathi-Serve](https://www.usenix.org/conference/osdi24/presentation/agrawal)
chia long prefill thành các chunk và ghép chunk vào batch decode đang chạy. Mục tiêu
là giới hạn thời gian mỗi iteration để prefill mới không gây generation stall.

Các kết quả có ích cho thiết kế benchmark:

- Prefill có thể bão hòa compute ở độ dài tương đối nhỏ, nên một prompt 13K–27K
  không cần chạy như một khối duy nhất.
- Chunk nhỏ bảo vệ time-between-token nhưng tăng scheduling/kernel overhead.
- Trong cấu hình Yi-34B của paper, chunk 512 có thể thêm khoảng 25% prefill overhead,
  còn budget 2048 gần như không còn overhead. Đây là evidence về hình dạng
  trade-off, không phải giá trị tối ưu cho Qwen/H200.
- Paper dùng budget 512 cho strict TBT SLO và 2048 cho relaxed SLO; budget phải
  phụ thuộc model, phần cứng và latency objective.

Hệ quả cho challenge:

1. First-pass sweep: `2048`, `4096`, `8192` batched tokens.
2. Nếu TPOT mean/p95 vẫn trên 25/35ms, thêm `512` và `1024`.
3. Chỉ thử `16384` khi TPOT đã tốt nhưng TTFT/throughput còn là bottleneck.
4. So sánh TTFT theo vị trí request trong từng burst; mean toàn trace có thể che
   generation stalls ở request đầu/cuối burst.

`max-num-batched-tokens` của vLLM không nên được xem là hoàn toàn tương đương mọi
chi tiết scheduler của Sarathi-Serve. Paper cung cấp hypothesis; trace replay mới
chọn được flag.

## 2. Prefix caching và shared-prefix attention

### vLLM/PagedAttention

[PagedAttention](https://doi.org/10.1145/3600006.3613165) (SOSP 2023) quản lý KV cache theo block để
giảm fragmentation và hỗ trợ chia sẻ cache giữa requests. Đây là lý do vLLM có thể
giữ batch lớn hơn các hệ thống phân bổ KV liên tục theo sequence.

Áp dụng trực tiếp:

- Bật APC trong candidate chính.
- Đo cached tokens, cache hit rate, eviction, preemption và KV occupancy.
- Không chỉ so APC on/off ở aggregate. Trace phải cho hit cao hơn qua burst 2–6;
  nếu không, cache residency hoặc hybrid-cache path đang có vấn đề.

PagedAttention tránh lưu trùng prefix nhưng không tự loại mọi redundant memory read
khi nhiều sequence cùng attend vào shared prefix trong decode.

### Prompt Cache

[Prompt Cache](https://proceedings.mlsys.org/paper_files/paper/2024/hash/a66caa1703fe34705a4368c3014c1966-Abstract-Conference.html)
(MLSys 2024) precompute và tái sử dụng attention states của các prompt modules như
system message, template hoặc document. Paper báo TTFT cải thiện mạnh nhất ở prompt
dài và giữ nguyên output vì không sửa weights.

Trace đã có đúng một module tự nhiên: system prefix 6.4K tokens. Tuy nhiên không
cần triển khai schema/markup của paper; APC theo exact token prefix đã bao phủ use
case. Paper củng cố metric cần đo là cached prefill tokens và TTFT, không phải TPOT.

### SGLang/RadixAttention

[SGLang](https://proceedings.neurips.cc/paper_files/paper/2024/hash/724be4472168f31ba1c9ac630f15dec8-Abstract-Conference.html)
(NeurIPS 2024) tổ chức KV cache bằng radix tree và dùng
cache-aware scheduling/eviction để tái sử dụng các prefix động. Cấu trúc này khớp
rất sát trace: một root system prompt, 20 nhánh conversation, mỗi nhánh dài thêm
qua 5 burst.

Hướng dùng:

- Không đổi runtime trước khi có best vLLM/APC profile.
- Nếu vLLM hybrid APC có hit thấp hoặc eviction bất thường, benchmark SGLang như
  alternate runtime với cùng tokenizer, chat template và GPQA contract.
- So sánh `cached_tokens / raw_prompt_tokens`, không chỉ throughput headline.

Rủi ro: phải xác nhận đúng revision Qwen3.5, native MTP, text-only path và image
submission. Khả năng chạy model quan trọng hơn lợi thế radix tree trên lý thuyết.

### ChunkAttention

[ChunkAttention](https://aclanthology.org/2024.acl-long.623/) (ACL 2024) lưu shared
KV trong prefix tree và dùng two-phase partition để tăng data locality của attention
kernel. Paper đo kernel speedup 3.2–4.8× với system prefix 1K–4K tokens. Trace có
prefix 6.4K và burst 20, nên cơ chế rất phù hợp về hình dạng workload.

Đây chưa phải quick win:

- Cần kernel/runtime integration; vLLM APC không tự trở thành ChunkAttention.
- Qwen3.5 chỉ dùng full attention ở một phần backbone, nên gain end-to-end bị pha
  loãng bởi Gated DeltaNet layers và các kernel khác.
- Chỉ cân nhắc sau khi profiler chứng minh decode attention trên shared prefix là
  hotspot còn lại sau APC.

## 3. Speculative decoding và native MTP

### Speculative Decoding

[Fast Inference from Transformers via Speculative Decoding](https://proceedings.mlr.press/v202/leviathan23a)
dùng model nhỏ để draft nhiều token và target model verify song song, với sampling
scheme giữ nguyên output distribution. Speedup phụ thuộc draft cost và acceptance
rate; không phải cứ tăng số speculative tokens là nhanh hơn.

Không thêm draft model riêng cho challenge:

- Target chỉ 2B nên draft overhead tương đối lớn.
- 18GB VRAM cần ưu tiên prefix cache.
- Qwen3.5 đã có native MTP head, tránh thêm một bộ weights/runtime path.

### MTP, Medusa và EAGLE

[Better & Faster Large Language Models via Multi-token Prediction](https://proceedings.mlr.press/v235/gloeckle24a.html)
(ICML 2024) huấn luyện nhiều future-token heads trên shared trunk và báo inference
có thể nhanh hơn trong cấu hình paper. Đây là evidence peer-reviewed gần nhất cho
native MTP head của Qwen3.5.

[Medusa](https://proceedings.mlr.press/v235/cai24b.html) tạo tree candidates từ
nhiều decoding heads rồi verify song song. [EAGLE](https://proceedings.mlr.press/v235/li24bt.html)
(ICML 2024) draft ở feature level để giảm token-level uncertainty. Hai paper cho
thấy speculative speedup phụ thuộc chất lượng proposal và verification overhead,
không chỉ số lượng draft tokens.

Không chuyển trực tiếp headline speedup của các paper sang Qwen3.5:

- Heads, acceptance method, model size và backend khác nhau.
- Trace có output cap 200 nhưng long-prefill rất lớn.
- MTP thêm speculative work/state và có thể giảm prefix-cache residency.

Gate cho MTP-1:

```text
accepted_draft_tokens / drafted_tokens đủ cao
TPOT giảm
TTFT và ERS không giảm
prefix hit rate không giảm đáng kể
KV eviction/preemption không tăng
GPQA giữ qua quality gate
```

Chỉ thử MTP-2 sau khi MTP-1 qua toàn bộ gate. Không triển khai Medusa/EAGLE riêng:
fixed Qwen model đã có MTP head, và một draft architecture nữa chỉ tăng code,
weights và attribution risk.

## 4. KV-cache và weight/activation quantization

### KIVI và KVQuant

[KIVI](https://proceedings.mlr.press/v235/liu24bz.html) chỉ ra Key và Value có phân
phối khác nhau và dùng asymmetric 2-bit quantization. [KVQuant](https://proceedings.neurips.cc/paper_files/paper/2024/hash/028fcbcf85435d39a40c4d61b42c99a4-Abstract-Conference.html)
kết hợp per-channel/pre-RoPE/non-uniform quantization cùng xử lý outlier để đạt
sub-4-bit KV cache.

Hai paper hỗ trợ ba kết luận:

1. KV capacity tăng có thể cho phép batch/context lớn hơn.
2. Quantization axis, scale và outlier handling ảnh hưởng chất lượng; số bit không
   đủ để mô tả thuật toán.
3. Memory saving không tự động thành latency gain nếu backend thiếu fused kernel.

Nhưng chúng không chứng minh `--kv-cache-dtype=fp8` của vLLM sẽ có cùng speedup
hoặc quality trên Qwen3.5 hybrid. Vì vậy:

- BF16 KV là control.
- FP8 KV là challenger đầu tiên khi có eviction/preemption.
- Chạy GPQA và replay trace; không dựa chỉ vào perplexity paper.
- 2/3-bit custom KV là research path sau FP8, không phải submission path đầu tiên.

### SmoothQuant

[SmoothQuant](https://proceedings.mlr.press/v202/xiao23c.html) (ICML 2023) chuyển
activation outlier difficulty sang weights bằng biến đổi tương đương rồi chạy W8A8.
Paper cho thấy quantization cần cả numerical recipe lẫn kernel hiệu quả; giảm bytes
không đảm bảo giảm latency.

Với challenge, SmoothQuant chỉ hỗ trợ thứ tự thử nghiệm: BF16 control, FP8 trên
Hopper, sau đó mới INT8/W8A8 nếu runtime path được hỗ trợ. Vì GPQA chỉ có 100 câu,
mọi weight/activation quantization phải chạy full quality gate; không dùng kết quả
“negligible accuracy loss” trên model/dataset khác để miễn validation.

## 5. Hopper kernels và hybrid architecture

### FlashAttention-3

[FlashAttention-3](https://proceedings.neurips.cc/paper_files/paper/2024/hash/7ede97c3e082c6df10a8d6103a2eebd2-Abstract-Conference.html)
(NeurIPS 2024) dùng Hopper TMA/WGMMA,
warp-specialization và overlap GEMM-softmax. Paper báo forward attention nhanh hơn
FlashAttention-2 khoảng 1.5–2.0× trên H100 và có FP8 path với block quantization.

H200 cùng họ Hopper nên hướng phần cứng phù hợp, nhưng cần bốn kiểm tra:

- BTC image/vLLM version có thật sự dispatch kernel đó cho Qwen3.5 không.
- Kernel có hỗ trợ head dimension, dtype và hybrid-cache layout của model không.
- MIG partition có đủ SM/bandwidth để tái hiện full-H100 microbenchmark không.
- Attention chiếm bao nhiêu phần trăm end-to-end sau khi APC loại phần lớn prefill.

Không nhân trực tiếp speedup kernel với ERS. Dùng profiler và một backend A/B trong
cùng runtime trước khi cân nhắc custom image/kernel.

### Gated DeltaNet

[Gated Delta Networks](https://openreview.net/forum?id=r8H7xhYPwz) mô tả recurrent
linear state kết hợp gating và delta rule, đồng thời nghiên cứu hybrid với attention.
Ý nghĩa ở đây là boundary: Qwen3.5 không phải Transformer full-attention thuần.

Do đó:

- KV quantization chỉ tác động phần cache mà backend thực sự lưu dưới dạng KV.
- Prefix caching còn phải quản lý recurrent/attention hybrid state đúng cách.
- FlashAttention optimization chỉ tăng tốc full-attention layers.
- Mọi headline từ Llama/Mistral cần đo lại trên Qwen3.5.

Paper này giải thích kiến trúc, không cung cấp recipe serving trực tiếp.

## 6. Paper hữu ích nhưng ngoài hardware contract

[DistServe](https://www.usenix.org/conference/osdi24/presentation/zhong-yinmin)
(OSDI 2024) tách prefill compute-intensive khỏi decode memory-intensive trên các
GPU khác nhau. Paper xác nhận TTFT và TPOT cạnh tranh tài nguyên khi colocate.

Challenge chỉ cấp một MIG device, nên không có nơi tách phase và không nên giả lập
bằng CPU offload. Insight cần giữ là metric:

- TPOT của decode đang chạy khi một long prefill mới được admit.
- Generation stall theo burst.
- Queue time, preemption và số request chồng giữa hai burst.

Chunked prefill là phương án single-GPU phù hợp hơn disaggregation.

## Nguồn phụ không dùng làm evidence chính

Hydragen, Preble, Splitwise và DeepSeek-V3 Technical Report có insight liên quan,
nhưng phiên bản đã kiểm tra là workshop paper, preprint hoặc technical report.
Chúng được loại khỏi ma trận quyết định để giữ đúng yêu cầu venue peer-reviewed.
Các kỹ thuật cốt lõi của chúng đã có đại diện mạnh hơn trong Prompt Cache,
ChunkAttention, SGLang, DistServe và paper MTP tại ICML.

## Experiment ladder rút ra từ literature

| ID | Profile | Hypothesis | Gate |
| --- | --- | --- | --- |
| P0 | BF16, text-only, 28K, APC on, MTP off | control hợp trace | 120/120 success, GPQA control |
| P1 | APC off | định lượng cache contribution | P0 phải thắng rõ ở burst 2–6 |
| P2 | token budget 2048/4096/8192 | tìm TTFT/TPOT frontier | ERS median và p10 tốt nhất |
| P3 | thêm 512/1024 nếu TPOT xấu | bảo vệ decode khỏi prefill stall | TPOT tăng điểm đủ bù TTFT |
| P4 | `max-num-seqs` 20/24/32 | admission vs cache pressure | không tăng timeout/eviction |
| P5 | GPU memory utilization .90/.93/.95 | tăng cache residency | không OOM/preemption regression |
| P6 | FP8 KV | giữ prefix working set lâu hơn | hit rate/ERS tăng, GPQA đạt gate |
| P7 | native MTP-1 | giảm TPOT | ERS tăng, acceptance/cache đạt gate |
| P8 | MTP-2 | thêm speculative depth | chỉ chạy nếu P7 thắng ổn định |
| P9 | attention backend/kernel | khai thác Hopper | end-to-end ERS tăng, không chỉ kernel |
| P10 | SGLang/RadixAttention | prefix-tree reuse tốt hơn | vượt best vLLM qua ≥3 runs |

Không gộp FP8 KV, MTP và runtime change trong một profile đầu tiên; sẽ không biết
optimization nào gây quality hoặc latency regression.

## Metrics paper-driven cần thêm vào report

Ngoài TTFT/TPOT/ERS tổng:

- TTFT theo `burst_id` và `position_in_burst`.
- TPOT khi không có prefill và khi đang có prefill chunks.
- Raw prompt tokens, computed prefill tokens và cached tokens từng request.
- Prefix hit rate riêng cho root system prompt và lineage prefix.
- KV occupancy trước/sau mỗi burst, eviction và preemption count.
- Scheduling iterations và prefill tokens mỗi iteration.
- Active sequences theo thời gian; overlap giữa hai burst.
- Speculative acceptance length/rate nếu bật MTP.
- GPU SM utilization, HBM bandwidth và attention/Gated-Delta kernel breakdown.
- GPQA answer diff cho mọi thay đổi dtype, kernel math hoặc decoding path.

## Quyết định chưa được paper chứng minh

Các paper không thể trả lời thay benchmark:

- Token budget tối ưu trên Qwen3.5-2B và MIG H200.
- APC của vLLM có giữ đủ 20 lineage qua 5 giây với hybrid cache hay không.
- FP8 KV có giảm latency hay chỉ tăng capacity.
- Native MTP-1 có acceptance rate đủ cao trên synthetic trace content hay không.
- Kernel nào image `vllm-openai:v0.22.1` thực sự dispatch.
- Accuracy impact trên exact 100-question GPQA evaluator.

Vì vậy literature xác định experiment order và metrics; winner vẫn phải được chọn
bằng trace replay trên đúng image, model revision và MIG partition.
