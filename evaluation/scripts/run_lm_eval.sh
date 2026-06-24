#!/usr/bin/env sh
set -eu

: "${LM_EVAL_MODEL_TYPE:=local-chat-completions}"
: "${LM_EVAL_MODEL:=local/sample-chat-small}"
: "${LM_EVAL_BASE_URL:=http://vllm:8000/v1/chat/completions}"
: "${LM_EVAL_TASKS:=gsm8k}"
: "${LM_EVAL_BATCH_SIZE:=1}"
: "${LM_EVAL_LIMIT:=10}"
: "${LM_EVAL_NUM_FEWSHOT:=0}"
: "${LM_EVAL_OUTPUT_PATH:=/app/results/lm-eval}"
: "${LM_EVAL_EXTRA_ARGS:=}"

mkdir -p "$LM_EVAL_OUTPUT_PATH"

set -- lm_eval \
  --model "$LM_EVAL_MODEL_TYPE" \
  --model_args "model=$LM_EVAL_MODEL,base_url=$LM_EVAL_BASE_URL,num_concurrent=1" \
  --tasks "$LM_EVAL_TASKS" \
  --batch_size "$LM_EVAL_BATCH_SIZE" \
  --num_fewshot "$LM_EVAL_NUM_FEWSHOT" \
  --limit "$LM_EVAL_LIMIT" \
  --output_path "$LM_EVAL_OUTPUT_PATH" \
  --log_samples \
  --apply_chat_template

if [ -n "$LM_EVAL_EXTRA_ARGS" ]; then
  # shellcheck disable=SC2086
  set -- "$@" $LM_EVAL_EXTRA_ARGS
fi

exec "$@"
