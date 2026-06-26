"""US-005 tests: MLflow tracing config for LiteLLM serving."""

from __future__ import annotations

from pathlib import Path

from llm_local.config_paths import LITELLM_CONFIG_FILE, LITELLM_TRACING_CONFIG_FILE
from llm_local.serving.tracing import (
    litellm_tracing_env,
    prepare_litellm_runtime_config,
    prepare_litellm_serving,
    source_litellm_config,
    tracing_enabled,
)


def test_tracing_disabled_by_default():
    cfg = {"genai": {"tracing_enabled": False}}
    assert tracing_enabled(cfg) is False
    assert source_litellm_config(cfg) == LITELLM_CONFIG_FILE
    assert litellm_tracing_env(cfg) == {}


def test_tracing_enabled_selects_config_and_env():
    cfg = {
        "genai": {"tracing_enabled": True},
        "mlflow": {
            "tracking_uri_docker": "http://mlflow:5000",
            "experiments": {"serving_traces": "mlops-platform-serving-traces"},
        },
    }
    assert tracing_enabled(cfg) is True
    assert source_litellm_config(cfg) == LITELLM_TRACING_CONFIG_FILE
    env = litellm_tracing_env(cfg)
    assert env["MLFLOW_TRACKING_URI"] == "http://mlflow:5000"
    assert env["MLFLOW_EXPERIMENT_NAME"] == "mlops-platform-serving-traces"


def test_prepare_runtime_config_writes_active_file(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "llm_local.serving.tracing.ACTIVE_LITELLM_CONFIG",
        tmp_path / "litellm-config.yaml",
    )
    cfg = {"genai": {"tracing_enabled": False}}
    out = prepare_litellm_runtime_config(cfg)
    assert out.is_file()
    assert "local-vllm" in out.read_text()


def test_prepare_litellm_serving_off(tmp_path, monkeypatch):
    monkeypatch.setattr("llm_local.serving.tracing.ROOT", tmp_path)
    monkeypatch.setattr(
        "llm_local.serving.tracing.ACTIVE_LITELLM_CONFIG",
        tmp_path / "config" / "active" / "litellm-config.yaml",
    )
    env_file = tmp_path / "config" / "env" / "litellm.env"
    env_file.parent.mkdir(parents=True)
    env_file.write_text("HOST_PORT=18040\n")

    cfg = {"genai": {"tracing_enabled": False}}
    enabled = prepare_litellm_serving(cfg)
    assert enabled is False
    assert "MLFLOW_TRACKING_URI" not in env_file.read_text()
