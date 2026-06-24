# vLLM Serving

Docker Compose scaffold for the single promoted OpenAI-compatible vLLM runtime.

Configure `config/env/vllm.env` from `config/env/vllm.env.example` with the model path, served
model name, GPU settings, and image tag required by the selected release.

Validation only checks compose/config shape. Runtime proof belongs in story
evidence and release checks on a prepared GPU host.
