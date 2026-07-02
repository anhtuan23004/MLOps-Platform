#!/usr/bin/env python3
"""Run structured extraction with a trained LoRA adapter."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def load_system_prompt(path: Path) -> str:
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        for message in record.get("messages", []):
            if message.get("role") == "system":
                return str(message["content"])
    raise ValueError(f"system prompt not found in {path}")


def record_key(path: Path) -> tuple[int, str]:
    return (int(path.stem), path.name) if path.stem.isdigit() else (sys.maxsize, path.name)


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if len(args) != 1:
        print("Usage: predict_structured.py <config.json>", file=sys.stderr)
        return 1

    config = json.loads(Path(args[0]).read_text())
    input_dir = Path(config["input_dir"])
    output_dir = Path(config["output_dir"])
    files = sorted(input_dir.glob("*.txt"), key=record_key)
    if not files:
        raise RuntimeError(f"no .txt inputs found in {input_dir}")

    from unsloth import FastLanguageModel

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=config["adapter_path"],
        max_seq_length=int(config.get("max_seq_length", 2048)),
        dtype=None,
        load_in_4bit=True,
    )
    FastLanguageModel.for_inference(model)
    system_prompt = load_system_prompt(Path(config["prompt_sample"]))

    output_dir.mkdir(parents=True, exist_ok=True)
    for stale in output_dir.glob("*.json"):
        stale.unlink()

    for source_path in files:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": source_path.read_text()},
        ]
        input_ids = tokenizer.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
        ).to(model.device)
        available_tokens = int(config.get("max_seq_length", 2048)) - input_ids.shape[-1]
        if available_tokens <= 0:
            raise RuntimeError(f"prompt exceeds context window: {source_path}")
        outputs = model.generate(
            input_ids=input_ids,
            max_new_tokens=min(int(config.get("max_new_tokens", 2048)), available_tokens),
            do_sample=False,
            use_cache=True,
            pad_token_id=tokenizer.eos_token_id,
        )
        response = tokenizer.decode(
            outputs[0][input_ids.shape[-1] :],
            skip_special_tokens=True,
        ).strip()
        (output_dir / f"{source_path.stem}.json").write_text(response + "\n")

    print(f"[+] Structured predictions: {len(files)} -> {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
