# Release Promotion on a GPU VM

Runbook for proving **real serving** promotion and rollback on a prepared GPU host.

## Prerequisites

- Docker + NVIDIA drivers compatible with vLLM image in `config/runtime-catalog.yaml`
- Repo cloned with Python deps (`uv sync` or venv + `pip install -e ".[test]"`)
- At least **two models** in local inventory (`models/registry.yaml` assembled)
- `llm-net` Docker network (created automatically by `./llm-local serve vllm up`)

## Start serving stack

```bash
./llm-local serve vllm up
./llm-local serve litellm up
make test-platform SERVICE=vllm
make test-platform SERVICE=litellm
```

## Promotion workflow (dev)

```bash
# Release A
./llm-local release create --id rel-vm-a --name "VM release A" \
  --source <model-id-a> \
  --datasets train=ds-a,val=ds-a,test=ds-a \
  --config-ref training/unsloth/configs/README.md

./llm-local release attach-eval rel-vm-a --ref evaluation/results/a.json
./llm-local release submit rel-vm-a
./llm-local release approve rel-vm-a
./llm-local release promote rel-vm-a --to dev --apply-serving

# Release B (rollback target = A)
./llm-local release create --id rel-vm-b --name "VM release B" \
  --source <model-id-b> \
  --datasets train=ds-b,val=ds-b,test=ds-b \
  --config-ref training/unsloth/configs/README.md

./llm-local release attach-eval rel-vm-b --ref evaluation/results/b.json
./llm-local release submit rel-vm-b
./llm-local release approve rel-vm-b
./llm-local release promote rel-vm-b --to dev --apply-serving

# Rollback to A
./llm-local release rollback --env dev --apply-serving
```

## Verify

```bash
./llm-local release show rel-vm-a
./llm-local release validate
make release-check SERVICE=vllm

# Gateway smoke (optional)
./llm-local eval run --target litellm --num-requests 1 --model local-vllm
```

## Evidence to capture

Record in the US-002 story evidence block:

- `validated_at`, `host_type: gpu-runtime`, GPU model/driver
- `image_tags` for vLLM and LiteLLM
- `model_ids` promoted
- Commands run
- `data/release-registry/audit/events.jsonl` excerpt
