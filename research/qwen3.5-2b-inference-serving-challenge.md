# Hướng tối ưu Qwen3.5-2B inference serving — Phase 1

Ngày nghiên cứu: 2026-07-06

Trạng thái: đã phân tích trace; chưa có MIG H200 hoặc benchmark proof

## Kết luận

Đây là bài toán inference serving, không phải SFT hay chọn model. Model và revision
đã bị cố định là `Qwen/Qwen3.5-2B`; mục tiêu là tối đa hóa ERS trên 120 requests
trong khi giữ GPQA accuracy đủ qua gate.

Thứ tự tối ưu đề xuất:

1. Dựng BF16 baseline đúng image/model hash của ban tổ chức.
2. Bật text-only runtime và đặt context 28K theo trace thực tế.
3. Bật prefix caching: đây là optimization chính của trace, không phải tùy chọn phụ.
4. Sweep scheduler quanh burst size 20 để cân bằng TTFT/TPOT.
5. Giữ MTP tắt ở profile đầu; chỉ A/B MTP-1 sau khi prefix cache ổn định.
6. A/B FP8 KV cache, sau đó FP8 weights/activations.
7. Chỉ thử INT4, custom kernels hoặc đổi runtime sau khi các bước trên plateau.

Không offload CPU/NVMe trong baseline: máy chỉ có 3 CPU cores và 8GB RAM, nên
offload dễ đổi GPU bottleneck thành latency/host-memory bottleneck.

## Contract của phase 1

Theo đề bài được cung cấp:

| Hạng mục | Giá trị |
| --- | --- |
| Model | `Qwen/Qwen3.5-2B`, BF16 source weights, fixed hash |
| Traffic | 120 requests từ `trace-round1.jsonl` |
| GPU | một MIG H200, 18GB VRAM |
| Host | 3 CPU cores, 8GB RAM |
| OS/CUDA | Ubuntu 22.04, CUDA 12.x |
| Endpoint | OpenAI-compatible server, port 8000 |
| Baseline image | `vllm/vllm-openai:v0.22.1` theo digest BTC cung cấp |
| Performance | TTFT + mean TPOT |
| Quality | 100 GPQA Diamond questions so với BF16 reference |
| Submission | public Docker image + `docker-compose.yml` |

Đề bài gọi model là dense Transformer; model card chính thức mô tả chính xác hơn
là causal language model có vision encoder, với language backbone 2B dùng hybrid
Gated DeltaNet/full-attention stack và native MTP. Tối ưu phải theo implementation
Qwen3.5 thực tế của runtime, không theo giả định Transformer attention thuần.

## Đọc hàm điểm

Mỗi request lỗi, timeout hoặc trả 0 token nhận điểm 0. Request thành công có:

```text
S_request = 0.5 * s_ttft + 0.5 * s_tpot
s_ttft = clamp((1500 - TTFT_ms) / 1400, 0, 1)^2
s_tpot = clamp((45 - TPOT_ms) / 25, 0, 1)^2
```

Điểm tối đa khi `TTFT <= 100ms` và `TPOT <= 20ms`; metric về 0 lần lượt tại
`1500ms` và `45ms`. Do lũy thừa 2, latency xấu đi ở vùng giữa bị phạt nhanh.

### Độ nhạy

| TTFT | `s_ttft` xấp xỉ |
| ---: | ---: |
| 100ms | 1.000 |
| 300ms | 0.735 |
| 500ms | 0.510 |
| 800ms | 0.250 |
| 1,000ms | 0.128 |
| 1,500ms | 0.000 |

| TPOT | `s_tpot` |
| ---: | ---: |
| 20ms | 1.000 |
| 25ms | 0.640 |
| 30ms | 0.360 |
| 35ms | 0.160 |
| 40ms | 0.040 |
| 45ms | 0.000 |

TPOT có cửa sổ chỉ 25ms nên đặc biệt nhạy. Tuy nhiên không được tối ưu decode bằng
cách làm prefill starvation: TTFT chiếm đúng 50% điểm và request timeout nhận 0.

## Accuracy Gate

Giả sử BF16 reference accuracy là `0.40`:

```text
delta = 0.40 - team_accuracy
f(delta) = 1                         nếu delta <= 0.10
         = 1 - (delta - 0.10) / 0.06 nếu 0.10 < delta < 0.16
         = 0                         nếu delta >= 0.16
Score = 100 * ERS * f(delta)
```

| Team accuracy | Delta | Hệ số quality |
| ---: | ---: | ---: |
| >= 0.30 | <= 0.10 | 1.000 |
| 0.29 | 0.11 | 0.833 |
| 0.28 | 0.12 | 0.667 |
| 0.27 | 0.13 | 0.500 |
| 0.26 | 0.14 | 0.333 |
| 0.25 | 0.15 | 0.167 |
| <= 0.24 | >= 0.16 | 0.000 |

Vì chỉ có 100 câu, mỗi câu tương ứng một điểm phần trăm. Không nên nhắm đúng
`0.30`; target nội bộ nên ít nhất `0.32–0.33` để có margin cho nondeterminism,
prompt/template mismatch và khác biệt runtime.

## Bước 0 — Phân tích trace trước khi chỉnh flag

Nguồn là [trace-round1.jsonl](<../data/input 2/trace-round1.jsonl>), SHA-256
`346a08afab490ced837aa11b8d6d25fa5d37e15a4398d462ba470f3997572278`.
File có đủ 120 request ID `0..119`, timestamp tăng đơn điệu và không có dòng lỗi.

Token được đếm bằng `tokenizer.json` và chat template non-thinking chính thức của
`Qwen/Qwen3.5-2B`. Hash tokenizer dùng khi phân tích là
`5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42`.
Cần đối chiếu lại hash này với fixed model revision của BTC trước benchmark.

### Arrival và request contract

- 6 burst tại `0`, `5,000`, `10,000`, `15,000`, `20,000`, `25,000ms`.
- Mỗi burst có 20 request, cách nhau đúng `25ms`; burst kéo dài `475ms`.
- Có 5 khoảng nghỉ `4,525ms`; toàn trace kéo dài `25,475ms`.
- Burst arrival rate là 40 request/s; average trên toàn trace khoảng 4.71 request/s.
- Số message tăng theo burst: `2, 4, 6, 8, 10, 12`, mỗi mức đúng 20 request.
- Mọi request dùng `max_tokens=200`, `temperature=0`, `seed=42`.
- Body chỉ có `model`, `messages`, `max_tokens`, `temperature`, `seed`; không có
  `stream`, `top_p`, `stop` hoặc `logprobs`. Cần xác nhận replay harness có ép
  streaming hay đo TTFT bằng instrumentation riêng.

Arrival trace không đủ để suy ra peak active concurrency: cần response duration.
Tuy nhiên 20 request đến trong 475ms, nên scheduler phải được benchmark quanh burst
size 20. Nếu end-to-end latency vượt 4.525 giây, hai burst còn chồng lên nhau.

### Độ dài token sau chat template

| Messages | Requests | Input min | Input p50 | Input p95 | Input max | Max `input + output` |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | 20 | 12,936 | 12,949 | 12,958 | 12,966 | 13,166 |
| 4 | 20 | 15,819 | 15,834 | 15,851 | 15,853 | 16,053 |
| 6 | 20 | 18,703 | 18,721 | 18,735 | 18,744 | 18,944 |
| 8 | 20 | 21,585 | 21,600 | 21,629 | 21,632 | 21,832 |
| 10 | 20 | 24,465 | 24,488 | 24,508 | 24,509 | 24,709 |
| 12 | 20 | 27,346 | 27,374 | 27,396 | 27,398 | 27,598 |

Toàn trace có input p50 `20,165`, p95 `27,381`, max `27,398`. Vì output cap là
200, context tối thiểu là `27,598`. Chọn `--max-model-len=28672` cho profile chính:
margin 1,074 token (3.9%). Giữ profile `32768` để fallback nếu fixed revision hoặc
chat template của evaluator khác hash/template đã phân tích. Không dùng 262,144.

### Prefix reuse là đặc tính chi phối

System message giống hệt trên cả 120 request và dài 6,388 content tokens (6,393
tokens sau role framing). Ngoài ra, 20 request ở mỗi burst là 20 conversation
lineage: request `i+20` giữ nguyên toàn bộ messages của request `i` rồi thêm một
cặp assistant/user. Prefix progression được xác nhận đủ `2 -> 4 -> 6 -> 8 -> 10`
messages cho cả 20 lineage.

Ước lượng dưới đây floor reusable prefix theo block 16 token. Đây là upper bound
khi các block từ burst trước chưa bị evict:

| Burst | Raw input tokens | Reusable tokens | Tokens cần prefill | Giảm prefill |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 258,984 | 121,296 | 137,688 | 46.8% |
| 2 | 316,691 | 258,752 | 57,939 | 81.7% |
| 3 | 374,395 | 316,416 | 57,979 | 84.5% |
| 4 | 432,067 | 374,144 | 57,923 | 86.6% |
| 5 | 489,750 | 431,808 | 57,942 | 88.2% |
| 6 | 547,455 | 489,520 | 57,935 | 89.4% |
| **Tổng** | **2,419,342** | **1,991,936** | **427,406** | **82.3%** |

Con số 82.3% không phải throughput claim: hit rate thật còn phụ thuộc KV capacity,
hybrid-cache alignment và eviction trong khoảng 5 giây. Nhưng trace đủ mạnh để
đưa APC vào default profile. Benchmark phải ghi prefix-cache hit tokens, eviction,
KV occupancy và preemption để xác nhận mức lợi ích thực.

## Ứng dụng cụ thể vào challenge

### Vì sao thứ tự tối ưu phải bắt đầu từ prefill/cache

Nếu mọi request sinh đủ 200 tokens, toàn trace có tối đa `24,000` output tokens,
trong khi raw input là `2,419,342` tokens. Output chỉ tương đương khoảng `0.99%`
input. Ngay cả ở upper bound APC tốt nhất, server vẫn phải compute khoảng `427,406`
prefill tokens; output khi đó tương đương khoảng `5.6%` lượng prefill mới.

Do đó:

- APC, context sizing và chunked prefill tác động phần workload lớn nhất.
- MTP chỉ tác động tối đa 24K decode tokens, nên không thể là optimization đầu tiên.
- FP8 KV hữu ích khi nó giúp giữ prefix qua 5 giây; giảm dtype nhưng vẫn bị eviction
  thì không giải quyết được bottleneck.
- Weight quantization không cần để model 2B “fit” bằng mọi giá; giá trị chính là
  giải phóng memory/cache capacity hoặc dùng kernel nhanh hơn.

### Bản đồ paper → trace → thay đổi thực tế

| Insight | Dấu hiệu trong trace | Áp dụng thực tế | Metric phải cải thiện | Điều kiện rollback |
| --- | --- | --- | --- | --- |
| PagedAttention/APC | system prefix 6.4K; 20 lineage lặp sau 5 giây | `--enable-prefix-caching` | computed prefill tokens, TTFT burst 2–6, ERS | hit thấp, output khác hoặc server không ổn định |
| Prompt Cache/RadixAttention | prefix tree gồm một root và 20 nhánh | giữ cache locality; SGLang chỉ là challenger | lineage hit rate và eviction | runtime incompatibility hoặc ERS không hơn vLLM |
| Orca/Sarathi | 20 long prompts đến trong 475ms | chunked prefill; sweep token budget | TPOT khi prefill chạy, TTFT tail | TTFT hoặc TPOT làm ERS giảm |
| ChunkAttention | shared prefix dài và batch 20 | profiler trước; custom/shared-prefix kernel sau | attention kernel time, end-to-end ERS | chỉ kernel nhanh nhưng ERS không đổi |
| MTP/Medusa/EAGLE | output cap 200; decode nhỏ hơn prefill | native MTP-1 sau APC/scheduler | TPOT, accepted tokens, ERS | cache pressure hoặc TTFT tăng |
| KIVI/KVQuant | 20 context dài cần cùng tồn tại | FP8 KV trước, low-bit custom sau | KV occupancy, eviction, preemption | GPQA giảm hoặc latency không tốt hơn |
| FlashAttention-3 | H200 Hopper; context tới 27.4K | dùng backend có sẵn trước custom kernel | attention time và ERS | unsupported hybrid path hoặc chỉ microbenchmark thắng |
| DistServe | prefill/decode interference | không tách GPU; chỉ đo interference | TPOT during prefill | không áp dụng multi-GPU design |

### Ứng dụng 1 — Text-only và context 28K

Áp dụng ngay:

```yaml
- --language-model-only
- --max-model-len=28672
```

Kết quả mong đợi:

- Không profile/load vision path vốn không được dùng.
- Giảm memory và startup work dành cho maximum context 262K không xuất hiện trong
  trace.
- Giữ đủ max request `27,598` tokens với margin `1,074` tokens.

Proof tối thiểu:

- 120/120 request được accept; không có context-length error.
- GPQA output tương đương BF16 baseline.
- Peak VRAM và startup time không xấu hơn.

Nếu tokenizer/chat template tại fixed revision làm request vượt 28K, chuyển đúng
một bước lên 32K. Không quay lại 262K.

### Ứng dụng 2 — APC cho hai tầng prefix

APC có hai use case riêng:

1. **Intra-burst:** 20 request cùng system prefix 6.4K. Ngay burst đầu, upper bound
   đã giảm 46.8% prefill.
2. **Inter-burst:** request `i+20` nối conversation của request `i`. Burst 2–6 có
   upper bound giảm 81.7–89.4% nếu lineage blocks sống qua 5 giây.

Không chỉ nhìn aggregate cache hit. Report cần tách:

```text
root_prefix_cached_tokens
lineage_prefix_cached_tokens
computed_prefill_tokens
cache_evictions_before_next_burst
```

Cách đọc kết quả:

- Burst 1 tốt, burst 2–6 không tăng hit: cache không giữ lineage đủ lâu.
- Root hit nhưng lineage hit thấp: KV capacity/eviction là bottleneck; thử FP8 KV
  hoặc hạ admission trước khi thử MTP.
- Cả root và lineage đều thấp: kiểm tra chat-template/token hash, APC/hybrid mode
  và request routing trước khi tune scheduler.
- Hit cao nhưng TTFT không giảm: profiler attention/Gated-Delta path; cache lookup
  có thể đúng nhưng runtime vẫn recompute phần hybrid state.

### Ứng dụng 3 — Chunked prefill để bảo vệ TPOT

Khi burst mới đến, long-prefill có thể làm decode của request trước bị stall. Dùng
`--max-num-batched-tokens` để giới hạn lượng prefill được ghép trong một scheduler
iteration:

| Giá trị | Khi nên thử | Trade-off dự kiến |
| ---: | --- | --- |
| 2,048 | TPOT/tail decode xấu | bảo vệ decode; nhiều iterations hơn |
| 4,096 | balanced starting point | control đầu tiên |
| 8,192 | TTFT/throughput xấu nhưng TPOT còn tốt | prefill nhanh hơn; dễ gây decode stall hơn |
| 512/1,024 | TPOT vẫn vượt 35ms ở 2K | strict latency challenger; overhead cao |
| 16,384 | TPOT dưới 25ms nhưng TTFT còn cao | TTFT challenger cuối |

Kết hợp với `--max-num-seqs=24`: đủ chứa burst 20 và một ít overlap. A/B `20` để
giảm cache pressure, `32` chỉ khi telemetry cho thấy request từ hai burst thực sự
chồng nhau mà không gây preemption.

### Ứng dụng 4 — FP8 KV để giữ working set

FP8 KV không được bật chỉ vì H200 hỗ trợ FP8. Bật khi BF16 profile xuất hiện ít
nhất một trong các dấu hiệu:

- Lineage blocks bị evict trước burst kế tiếp.
- KV occupancy thường xuyên gần trần.
- Request bị preempt/recompute.
- `max-num-seqs=20/24` không giữ được working set dù model đã text-only/28K.

Nếu FP8 KV tăng cache hit và giảm recompute nhưng TPOT không đổi, profile vẫn có
thể thắng nhờ TTFT/ERS. Nếu không có KV pressure, thêm quant/dequant work có thể
không mang lợi ích.

### Ứng dụng 5 — Native MTP chỉ cho decode

MTP-1 phù hợp khi profile APC + scheduler đã có:

- Prefix hit cao và ổn định.
- Không có preemption/eviction đáng kể.
- TTFT đạt mức chấp nhận được nhưng TPOT còn trên khoảng 25–30ms.

Giữ MTP-1 nếu TPOT và ERS cùng tốt hơn qua ba run, acceptance rate ổn định và KV
pressure không tăng. Nếu TPOT tốt hơn nhưng ERS giảm, nguyên nhân thường là TTFT,
queueing hoặc cache residency xấu đi; tắt MTP thay vì cố tăng lên MTP-2.

### Ứng dụng 6 — Kernel hoặc runtime khác

SGLang/RadixAttention, ChunkAttention và FlashAttention-3 chỉ chuyển thành work
item khi profiler xác nhận bottleneck tương ứng:

| Profiler cho thấy | Challenger hợp lý |
| --- | --- |
| APC hit thấp do eviction policy/prefix-tree handling | SGLang/RadixAttention |
| Shared-prefix decode attention đọc KV lặp nhiều | ChunkAttention-like kernel |
| Full-attention kernels chiếm phần lớn GPU time | FlashAttention-3/backend A/B |
| Gated-Delta kernels chiếm phần lớn | không kỳ vọng FlashAttention giải quyết |

Không đổi runtime và kernel cùng lúc. Challenger phải dùng cùng model revision,
chat template, seed, trace và GPQA parser với vLLM control.

### Quy tắc quyết định từ kết quả benchmark

| Quan sát | Kết luận gần nhất | Hành động tiếp theo |
| --- | --- | --- |
| Burst 2–6 TTFT giảm mạnh so với burst 1 | APC hoạt động | tune scheduler; chưa cần đổi runtime |
| TPOT tăng khi burst mới bắt đầu | prefill/decode interference | giảm batch-token budget |
| TTFT cao, TPOT dưới 25ms | prefill bị chia quá nhỏ | tăng budget 4K → 8K |
| TPOT trên 35ms, TTFT còn margin | decode bị stall | giảm 4K → 2K → 1K |
| Cache hit thấp và KV gần đầy | cache capacity thiếu | FP8 KV hoặc `max-num-seqs=20` |
| Cache hit cao nhưng ERS thấp | scheduler/kernel bottleneck | tune budget rồi profile kernels |
| MTP giảm TPOT nhưng tăng TTFT/eviction | speculative pressure | bỏ MTP |
| Quantization tăng tốc nhưng GPQA < 0.32 | quality gate thất bại | rollback precision profile |
| Profile chỉ thắng một run | noise/warm-up effect | không promote; chạy lại ≥3 lần |

## Bước 1 — Baseline có thể tin cậy

Giữ BF16 source weights và image/digest của BTC. Chạy ít nhất ba lần cùng trace:

- Warm/cold TTFT, mean TPOT và ERS từng request.
- Throughput, request failures, queue time và preemptions.
- GPU utilization, peak VRAM và KV-cache occupancy.
- GPQA exact prompt, chat template, sampling params và seed.
- Container startup/readiness time.

Không thay nhiều flag trong baseline. Nếu kết quả lặp lại không ổn định thì chưa
được dùng làm control cho quantization.

### Thinking-mode contract

Qwen3.5-2B mặc định non-thinking, nhưng server có thể override qua chat-template
kwargs. Không bật thinking toàn cục để cố tăng GPQA nếu trace/reference không dùng
cùng contract: reasoning làm output dài hơn, tăng TPOT workload và có thể đổi cách
answer parser đọc đáp án. Baseline và mọi challenger phải giữ nguyên
`enable_thinking`, prompt, stop conditions và sampling parameters của evaluator.

## Bước 2 — Text-only runtime

Qwen3.5 là unified VLM nhưng phase 1 chỉ dùng text. Model card Qwen và vLLM recipe
đều khuyến nghị `--language-model-only` để bỏ vision encoder/multimodal profiling
và dành thêm memory cho KV cache:

```yaml
command:
  - --model=/model
  - --served-model-name=Qwen3.5-2B
  - --language-model-only
```

Đây là thay đổi ít rủi ro nhất vì không sửa language weights hoặc decoding math.
Vẫn phải kiểm tra GPQA bit-for-bit/exact-answer-equivalent với baseline.

## Bước 3 — Scheduler sweep

vLLM V1 dùng chunked prefill khi có thể. Tài liệu vLLM mô tả trade-off:

- `max_num_batched_tokens` nhỏ hơn ưu tiên ITL/TPOT.
- Giá trị lớn hơn cải thiện TTFT và throughput cho small models.

Trace là long-prefill, output ngắn và burst size 20. Sarathi-Serve cho thấy chunk
nhỏ bảo vệ decode latency nhưng tăng prefill overhead; giá trị tối ưu phụ thuộc
model, phần cứng và SLO. Vì vậy dùng sweep có kiểm soát thay vì coi 8K là default:

| Parameter | Candidate values ban đầu |
| --- | --- |
| `--max-num-batched-tokens` | 2048, 4096, 8192; thêm 512/1024 nếu TPOT xấu |
| `--max-num-seqs` | 24 control; A/B 20 và 32 |
| `--gpu-memory-utilization` | 0.90, 0.93, 0.95 |
| `--max-model-len` | 28672 control; 32768 compatibility fallback |

Chọn theo final score distribution, không chỉ mean throughput. Ghi riêng request
ở p95/p99 vì vài timeout có thể xóa lợi ích trung bình.

## Bước 4 — Prefix caching

Bật `--enable-prefix-caching` trong candidate chính. Trace có chung system prefix
6.4K tokens và 20 multi-turn lineages lặp lại sau mỗi 5 giây; upper bound giảm
prefill là 82.3%. APC không đổi output và không trực tiếp cải thiện decode/TPOT,
nhưng giảm lượng long-prefill cạnh tranh với decode.

Vẫn giữ một APC-off control để đo attribution. vLLM recipe ghi prefix caching cho
Mamba/Gated-Delta cache `align` mode còn experimental; với Qwen3.5 phải kiểm tra
output correctness, hit rate, eviction và server stability. Nếu cache không giữ
được 20 lineage qua 5 giây, FP8 KV hoặc hạ `max-num-seqs` có thể đáng giá hơn MTP.

Không dùng semantic cache ở vòng đầu. Approximate matching có thể trả output của
request khác, gây accuracy/reproducibility risk và khó chứng minh hợp lệ theo luật.

## Bước 5 — Native MTP

Qwen3.5-2B có MTP head. Model card chính thức đưa cấu hình vLLM:

```yaml
- --speculative-config={"method":"qwen3_next_mtp","num_speculative_tokens":2}
```

Trace này có burst 20 request, input 13K–27.4K và output cap chỉ 200. Đây là workload
prefill/cache-bound trước khi chứng minh ngược lại; speculative KV có thể làm giảm
capacity dành cho prefix blocks. Vì vậy MTP-off là control và candidate mặc định.

Chỉ A/B MTP-1 sau khi APC/scheduler ổn định. Chỉ thử MTP-2 nếu MTP-1 có acceptance
rate cao, không tăng eviction/preemption và cải thiện ERS qua ít nhất ba run. Thu thập:

- Accepted speculative tokens / drafted tokens.
- TPOT và TTFT.
- KV-cache occupancy và max concurrency.
- ERS và GPQA.

vLLM recipe cảnh báo MTP-1 có thể giảm per-token latency nhưng làm throughput xấu
ở high concurrency vì speculative tokens tiêu thụ KV capacity. Với trace này,
không bật MTP-2 chỉ dựa trên việc model card cung cấp ví dụ hai speculative tokens.

## Bước 6 — FP8 KV cache

FP8 KV cache gần như nhân đôi dung lượng token cache theo tài liệu vLLM, hữu ích
khi có preemption hoặc concurrency cao:

```yaml
- --kv-cache-dtype=fp8
- --calculate-kv-scales
```

Nhưng FP8 KV không tự động giảm latency ở mọi backend; lợi ích chính là capacity.
Chỉ bật nếu telemetry cho thấy KV pressure. Dùng calibrated scales nếu luật và
workflow cho phép; on-the-fly scale là baseline, không phải quality optimum.

Gate:

- GPQA >= 0.32 nội bộ.
- Không tăng request failures/preemptions.
- ERS phải tăng qua nhiều run, không chỉ một lần.

## Bước 7 — Weight/activation quantization

Thứ tự:

1. BF16 control.
2. FP8 W8A8/per-tensor hoặc per-block nếu vLLM 0.22.1 và Qwen3.5 path hỗ trợ ổn định.
3. INT8.
4. INT4 AWQ/GPTQ chỉ khi cần thêm concurrency và vẫn qua Accuracy Gate.

H200 hỗ trợ FP8 tốt, nhưng support phần cứng không chứng minh Qwen3.5 hybrid kernels
được tăng tốc trong đúng runtime. MIG 18GB cũng chỉ là một lát của H200, không có
toàn bộ compute/bandwidth của card. Mọi quant profile phải ghi:

- Model/source hash và quant recipe/calibration hash.
- GPQA answer diff so với BF16.
- TTFT/TPOT/ERS từng request.
- Startup time và peak host RAM.

Không giả định INT4 nhanh hơn FP8/BF16 cho model 2B. Dequant overhead và kernel
coverage có thể làm TPOT xấu hơn dù weights nhỏ hơn.
Online quantization còn có thể tăng transient host RAM lúc load; giới hạn 8GB RAM
phải được đo trong startup, không chỉ theo steady-state GPU memory.

## Các hướng không ưu tiên

| Hướng | Lý do chưa ưu tiên |
| --- | --- |
| CPU/NVMe offload | 3 CPU cores, 8GB RAM; latency cao |
| Tensor parallel | chỉ một MIG device |
| Draft model riêng | thêm weights/KV/cache và tuning complexity; native MTP có sẵn |
| Semantic cache | accuracy/legal equivalence khó chứng minh |
| Full 262K context | lãng phí nếu trace không cần |
| Custom CUDA/Triton ngay | chi phí cao trước khi scheduler/MTP/FP8 plateau |
| Đổi SGLang/TensorRT-LLM ngay | mất baseline tương thích submission; chỉ thử sau vLLM plateau |
| Fine-tune model | ngoài trọng tâm fixed-weight serving và có thể vi phạm fixed hash |

## Experiment ladder

Mỗi row chỉ thay một nhóm biến và phải chạy GPQA khi precision/math thay đổi.

| ID | Thay đổi | GPQA cần chạy | Điều kiện giữ |
| --- | --- | --- | --- |
| R0 | BTC BF16 baseline | có | reproducible |
| R1 | `--language-model-only` | có một lần | output tương đương, VRAM giảm |
| R2 | `max-model-len=28672` | không nếu output giữ nguyên | 0 rejected request, ERS tăng |
| R3 | prefix cache on/off | không | hit rate/TTFT/ERS tăng, output giữ nguyên |
| R4 | token budget + 24 seqs quanh burst 20 | không | ERS median/p10 tăng |
| R5 | MTP off/1; 2 chỉ khi MTP-1 đạt gate | có | ERS tăng, cache pressure không xấu |
| R6 | FP8 KV | có | capacity/ERS tăng, quality giữ |
| R7 | FP8 weights/activations | bắt buộc | final score tăng |
| R8 | INT4 | bắt buộc | final score tăng đủ bù quality risk |
| R9 | alternate runtime/custom kernels | bắt buộc | vượt best vLLM profile ổn định |

## Candidate compose profiles

Đây là trace-derived starting point, chưa phải cấu hình thắng khi chưa chạy trên
MIG H200. Giữ entrypoint bắt buộc của BTC và thêm flags theo profile.

### Safe profile

```yaml
command:
  - --model=/model
  - --served-model-name=Qwen3.5-2B
  - --host=0.0.0.0
  - --port=8000
  - --tensor-parallel-size=1
  - --language-model-only
  - --max-model-len=28672
  - --gpu-memory-utilization=0.93
  - --max-num-batched-tokens=4096
  - --max-num-seqs=24
  - --enable-prefix-caching
```

Giữ một control giống hệt nhưng bỏ `--enable-prefix-caching`. Nếu profile 28K reject
request do evaluator template khác, chuyển sang 32K; không tăng thẳng lên 262K.

### Throughput/capacity challenger

Thêm sau khi R1–R4 ổn định:

```yaml
  - --kv-cache-dtype=fp8
  - --calculate-kv-scales
```

### TPOT challenger

Thêm riêng, không gộp ngay với FP8 để attribution rõ:

```yaml
  - --speculative-config={"method":"qwen3_next_mtp","num_speculative_tokens":1}
```

MTP-2 là challenger vòng sau, không phải default trace profile.

## Benchmark report bắt buộc

Mỗi profile phải lưu:

```text
profile_id
docker_image_digest
model_revision
runtime_flags
trace_hash
run_seed
request_count / success / timeout / zero-token
TTFT p50/p90/p95/p99 + per-request values
TPOT mean/p50/p90/p95/p99 + per-request values
ERS mean + per-request score
GPU peak memory/utilization
KV occupancy/preemptions
GPQA correct/100, delta, quality factor
final score
```

Không chọn profile từ một run. Dùng ít nhất ba performance runs; profile đứng đầu
phải vượt control ở median và không có tail regression làm tăng zero-score requests.

## Việc cần có trước khi chốt flags

1. Model hash và tokenizer/chat-template hash chính thức.
2. Replay harness có ép `stream=true` hay đo TTFT bằng instrumentation riêng.
3. Quy định có cho phép materialize quantized derivative weights hay chỉ runtime
   quantization từ `/model`.
4. BTC có tính startup/warm-up trong timeout hay chỉ benchmark sau readiness.
5. Exact GPQA prompt, answer parser, sampling params và seed.
6. Healthcheck contract và startup deadline.
7. Xác nhận `vllm-openai:v0.22.1` có đúng flags Qwen3.5/MTP/FP8 định dùng.

## Liên hệ với research SFT

Tài liệu [Qwen text model comparison](qwen-text-model-comparison.md) phục vụ bài
toán y khoa tự chọn model và SFT. Phase 1 này cố định Qwen3.5-2B và chỉ tối ưu
serving. Không dùng kết luận chọn Qwen3-8B/Qwen3-4B của tài liệu SFT để thay model
trong submission phase 1.

Phần nền tảng học thuật và experiment hypotheses được tổng hợp riêng tại
[Peer-reviewed papers cho Qwen3.5 serving](qwen3.5-serving-optimization-papers.md).

## Nguồn

- Đề bài/quy định phase 1 do người dùng cung cấp ngày 2026-07-06.
- [Qwen3.5-2B official model card](https://huggingface.co/Qwen/Qwen3.5-2B)
- [vLLM Qwen3.5 recipe](https://github.com/vllm-project/recipes/blob/main/Qwen/Qwen3.5.md)
- [vLLM optimization and tuning](https://docs.vllm.ai/en/stable/configuration/optimization/)
- [vLLM automatic prefix caching](https://docs.vllm.ai/en/v0.15.0/features/automatic_prefix_caching/)
- [vLLM quantized KV cache](https://docs.vllm.ai/en/v0.18.0/features/quantization/quantized_kvcache/)
- [vLLM online quantization](https://docs.vllm.ai/en/latest/features/quantization/online/)
- [vLLM MTP documentation](https://docs.vllm.ai/projects/speculators/en/latest/user_guide/algorithms/mtp/)
