# Model Releases — MLOps-Platform

Product contract for the **release registry**: durable promotion metadata separate
from the local model inventory in `models/registry.yaml`.

Source lifecycle doc: [`model-release-lifecycle.md`](model-release-lifecycle.md).

## Storage layout

Default root: `data/release-registry/` (gitignored). Override with `RELEASE_REGISTRY_ROOT`.

```
data/release-registry/
  releases/<release_id>.yaml
  aliases/dev.yaml
  aliases/staging.yaml
  aliases/prod.yaml
  audit/events.jsonl
```

## Release record (schema v1)

| Field | Required | Notes |
| --- | --- | --- |
| `release_id` | yes | Unique identifier |
| `name` | yes | Human-readable name |
| `promotion_state` | yes | `draft`, `candidate`, `approved`, `promoted`, `retired` |
| `source_artifact` | yes | Model inventory ID (maps to vLLM via `llm_local.models.manage`) |
| `dataset_versions` | yes | `train`, `val`, `test` splits with `id` + optional `checksum` |
| `training_config_ref` | yes | Immutable reference to training config |
| `eval_report_ref` | staging+ | Path/URI to evaluation report |
| `serving_bundle_ref` | prod | Path/URI to serving bundle |
| `rollback_to_release_id` | staging+ | Previous release when promoted |
| `created_at`, `created_by` | yes | Audit metadata |
| `approved_by` | when approved | Who approved |

## Promotion gates

| Action | State required | Extra requirements |
| --- | --- | --- |
| `submit` | `draft` | lineage fields complete |
| `approve` | `candidate` | `eval_report_ref` |
| `promote --to dev` | `candidate` or `approved` | — |
| `promote --to staging` | `approved` | `eval_report_ref`, alias must have rollback context |
| `promote --to prod` | `approved` | `eval_report_ref`, `serving_bundle_ref`, rollback context |
| `rollback --env <env>` | alias has `previous_release_id` | swaps active/previous |

## CLI

```bash
./llm-local release create --id ID --name NAME --source MODEL_ID \
  --datasets train=ds1,val=ds2,test=ds3 --config-ref PATH

./llm-local release attach-eval ID --ref evaluation/results/report.json
./llm-local release submit ID
./llm-local release approve ID
./llm-local release promote ID --to dev|staging|prod [--apply-serving|--no-apply-serving]
./llm-local release rollback --env dev|staging|prod [--apply-serving|--no-apply-serving]
./llm-local release validate
```

## Real serving integration

When `--apply-serving` is enabled (default when Docker is available):

1. Resolve `source_artifact` → `llm_local.models.manage select`
2. Restart vLLM (unless `--no-restart`)
3. Wait for health endpoint + run `llm_local.ops.preflight vllm`

Use `--no-apply-serving` for metadata-only workflows (CI compose tests).

VM proof: see [`docs/runbooks/release-promotion-vm.md`](../runbooks/release-promotion-vm.md).

## Implementation status

| Capability | Status |
| --- | --- |
| File registry + gates | implemented (US-002) |
| CLI via `llm-local release` | implemented (US-002) |
| Compose metadata integration test | implemented (US-002) |
| VM platform proof (live vLLM promote/rollback) | requires prepared GPU host |
