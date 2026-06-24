"""Model inventory data paths (weights and YAML live under repo models/)."""

from llm_local.catalog import ROOT

MODELS_DATA_DIR = ROOT / "models"
REGISTRY_FILE = MODELS_DATA_DIR / "registry.yaml"
DESIRED_MODELS_FILE = MODELS_DATA_DIR / "desired-models.yaml"
PRESETS_FILE = MODELS_DATA_DIR / "presets.yaml"
