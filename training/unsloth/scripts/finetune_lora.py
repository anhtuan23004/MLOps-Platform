#!/usr/bin/env python3
"""LoRA fine-tune entrypoint for the Unsloth training container (US-004)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def load_config(path: Path) -> dict:
    return json.loads(path.read_text())


def write_summary(
    output_dir: Path,
    config: dict,
    final_loss: float,
    *,
    rows_loaded: int | None = None,
    data_format: str | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "final_loss": final_loss,
        "epochs": config.get("epochs", 1),
        "adapter_type": config.get("adapter_type", "lora"),
        "base_model": config.get("base_model"),
        "dataset_id": config.get("dataset_id"),
    }
    if rows_loaded is not None:
        summary["rows_loaded"] = rows_loaded
    if data_format is not None:
        summary["data_format"] = data_format
    (output_dir / "training_summary.json").write_text(json.dumps(summary, indent=2) + "\n")


def simulate(config: dict, output_dir: Path) -> float:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "adapter_config.json").write_text(
        json.dumps(
            {
                "peft_type": config.get("adapter_type", "lora"),
                "base_model": config.get("base_model"),
                "r": config.get("lora_r", 16),
                "lora_alpha": config.get("lora_alpha", 16),
            },
            indent=2,
        )
        + "\n"
    )
    (output_dir / "README.txt").write_text("Simulated adapter (UNSLOTH_TRAIN_SIMULATE)\n")
    loss = 0.21
    write_summary(output_dir, config, loss)
    return loss


def train_with_unsloth(config: dict, output_dir: Path) -> float:
    from datasets import Dataset
    from transformers import TrainingArguments
    from trl import SFTTrainer
    from unsloth import FastLanguageModel
    import torch

    from llm_local.pipeline.dataset import DatasetValidationError, load_manifest_split

    model_path = config["base_model_path"]
    max_seq_length = int(config.get("max_seq_length", 2048))
    epochs = int(config.get("epochs", 1))
    learning_rate = float(config.get("learning_rate", 2e-4))
    batch_size = int(config.get("batch_size", 2))

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_path,
        max_seq_length=max_seq_length,
        dtype=None,
        load_in_4bit=True,
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=int(config.get("lora_r", 16)),
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        lora_alpha=int(config.get("lora_alpha", 16)),
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=3407,
    )

    try:
        data_format, records = load_manifest_split(
            Path(config["dataset_manifest"]),
            pipeline_root=Path(config["dataset_root"]),
            split=str(config.get("dataset_split", "train")),
        )
    except DatasetValidationError as exc:
        raise RuntimeError(f"dataset load failed: {exc}") from exc

    dataset = Dataset.from_list(records)

    max_steps = max(10, epochs * 10)
    trainer_kwargs: dict = {
        "model": model,
        "processing_class": tokenizer,
        "train_dataset": dataset,
        "max_seq_length": max_seq_length,
        "args": TrainingArguments(
            per_device_train_batch_size=batch_size,
            gradient_accumulation_steps=2,
            warmup_steps=2,
            max_steps=max_steps,
            learning_rate=learning_rate,
            fp16=not torch.cuda.is_bf16_supported(),
            bf16=torch.cuda.is_bf16_supported(),
            logging_steps=1,
            output_dir=str(output_dir),
            report_to=[],
        ),
    }
    if data_format == "text":
        trainer_kwargs["dataset_text_field"] = "text"

    trainer = SFTTrainer(**trainer_kwargs)
    train_result = trainer.train()
    final_loss = float(train_result.training_loss) if train_result.training_loss is not None else 0.2

    model.save_pretrained(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    write_summary(
        output_dir,
        config,
        final_loss,
        rows_loaded=len(records),
        data_format=data_format,
    )
    return final_loss


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args:
        print("Usage: finetune_lora.py <config.json>", file=sys.stderr)
        return 1

    config_path = Path(args[0])
    config = load_config(config_path)
    output_dir = Path(config.get("output_dir", "/workspace/pipeline/models/artifacts/staging"))

    if os.environ.get("UNSLOTH_TRAIN_SIMULATE", "").lower() in {"1", "true", "yes"}:
        simulate(config, output_dir)
        print(f"[+] Simulated fine-tune -> {output_dir}")
        return 0

    try:
        loss = train_with_unsloth(config, output_dir)
        print(f"[+] Unsloth fine-tune complete loss={loss:.4f} -> {output_dir}")
        return 0
    except ImportError as exc:
        print(f"ERROR: Unsloth dependencies missing: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: fine-tune failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
