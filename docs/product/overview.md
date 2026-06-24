# Product Overview — MLOps-Platform

## Vision

A reusable hybrid MLOps platform that helps teams move models from local
experimentation to production-like serving with explicit lineage, evaluation,
promotion, observability, and rollback.

## Users

- ML engineers preparing local or on-prem models for controlled release.
- Platform engineers standardizing model serving and validation workflows.
- Application developers consuming stable model aliases through a gateway.
- Researchers comparing model quality and latency before promotion.

## Domain Map

```text
Human intent / model change
  -> Feature intake
  -> Story packet
  -> Source model or artifact
  -> Training / conversion
  -> Evaluation
  -> Release metadata
  -> Promotion
  -> vLLM runtime
  -> LiteLLM gateway
  -> Observation and rollback
```

## Current State

This repo starts with inherited local LLM infrastructure and a blank harness.
Product-specific contracts, story packets, release gates, and production claims
must be rebuilt for MLOps-Platform through the harness workflow.
