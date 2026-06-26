# Harness Backlog

Use this file for process or harness friction discovered while building
MLOps-Platform.

## Open Items

| Item | Trigger | Proposal | Status |
| --- | --- | --- | --- |
| First release schema | Model release lifecycle story selected | Add schema template and validation command once fields are known. | candidate |
| Docker Hardened Images note | Runtime hardening or custom MLflow image story selected | Evaluate Docker Hardened Images as a base for custom Python workload images (for example MLflow 3.x built via `pip install`, release-registry test image, or future control-plane utilities). Initial fit looks strongest for CPU Python services because DHI provides hardened/minimal images, SBOM + provenance, Docker Scout policy workflow, and reduced package surface. It does **not** directly solve GPU runtime images like vLLM/Unsloth, and may add friction where shell/package-manager access is needed. Capture a reusable build template and validation check only when a story selects custom image hardening. | candidate |

## Capture Rule

When an agent finds repeated confusion, missing validation commands, stale docs,
or unclear handoff instructions, either improve the harness directly in the
current story or add a concrete proposal here.
