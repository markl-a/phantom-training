# Synthetic Eval/Judge Pipeline Scenario

`phantom-training` P3 adds a deterministic Tier 1 eval/judge scenario. It
combines the P2 training-planning bundle with the P2 backend lifecycle bundle,
then writes a reproducible reporting bundle for the proxy eval floor, hermetic
judge, reproducibility checks, and release gate.

Run it locally:

```powershell
python -m phantom_training.cli eval-judge-scenario --out <bundle-dir>
```

Or, after installation:

```powershell
phantom-train eval-judge-scenario --out <bundle-dir>
phantom-training-eval-judge-scenario --out <bundle-dir>
```

## Artifact Contract

The bundle writes these top-level files:

- `manifest.json`: schema version, mode, safety flags, source bundle references,
  and artifact map.
- `eval-report.json`: deterministic held-out proxy floor metrics.
- `judge-report.json`: deterministic hermetic judge summary.
- `reproducibility-report.json`: dataset-card, run-manifest, backend-stage, and
  public reproducibility status.
- `release-gate.json`: Tier 1 demo readiness and explicit real-training
  release blockers.
- `audit-summary.json`: metadata-only event summary.
- `summary.md`: short human-readable summary.

It also writes these source bundles:

- `training-demo/`: the deterministic P2 training-planning bundle.
- `backend-lifecycle/`: the deterministic P2 backend lifecycle validation
  bundle.

`manifest.json` must include:

```json
{
  "schema_version": 1,
  "mode": "synthetic_eval_judge_pipeline_scenario",
  "synthetic_only": true,
  "real_training": false,
  "model_artifacts_written": false,
  "external_network": false,
  "gpu_required": false,
  "publish_enabled": false
}
```

## Boundary

This scenario is Tier 1 deterministic plumbing only. The eval report is a proxy
floor, not a public benchmark or model evaluation claim. The judge report is a
hermetic local check, not model inference. The scenario performs no real
training, downloads no model, writes no adapter or weight artifact, requires no
GPU, uses no external network, and publishes nothing.

Before any real-training release, the project still needs a real backend
adapter, private-data policy review, model artifact scan, and explicit operator
approval.
