# LiteLLM Gateway

LiteLLM runs as the local OpenAI-compatible gateway for promoted vLLM model
aliases.

Configure `config/env/litellm.env` (copy from `config/env/litellm.env.example`) with
gateway auth and the upstream vLLM model binding rendered from the active serving
preset. Routing config: `config/litellm/config.yaml`.
