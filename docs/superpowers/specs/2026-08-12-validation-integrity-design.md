# Validation Integrity Design

## Goal

Prevent toolkit from producing successful validation, review, scoring, statistical, or reporting outputs when required evidence is missing or misclassified.

## Scope

Fix seven validated defects:

1. `report` emits hard-coded adoption results.
2. blind-review packets contain placeholder code.
3. `validate` succeeds when study inputs are absent.
4. skipped JUnit cases count as passes.
5. cluster bootstrap drops repeated sampled tasks.
6. prompt interaction always reports no blocking interaction.
7. default pytest discovery collects archived solution suites.

No unrelated refactoring or dependency additions.

## Design

### Study validation

`tdd-ablation validate --study PATH` requires an existing directory containing `preregistration.json` and `prompts/conditions.json`. Missing inputs raise `ContractError`; CLI returns status 1. Example preregistration files remain documentation, not runtime fallback.

### Report generation

`tdd-ablation report --study PATH --output PATH` reads `PATH/results.json`. File must contain `study_name`, `total_runs`, and `adoption_decision`; `adoption_decision` must contain `adopt` and `reasons`. Missing or malformed results fail closed. `render_report` remains pure and receives validated data.

Current repository receives `study/results.json` matching frozen final report so documented command remains operational without changing published outcome.

### Blind-review artifacts

`prepare_blind_review` gains required `artifact_source: Path` input. Source must be an existing directory. Function recursively copies artifact files while rejecting symlinks and excluding trace files by explicit names and suffixes. Manifest lists copied relative paths and selects `solution.py` as entry point when present. Packet never includes run ID, condition, prompt, trace, or execution metadata.

### JUnit scoring

`EvaluationRecord` gains `skipped_count`. Parser detects `<skipped>` separately. Skipped cases do not contribute passed count, failed count, weights, score denominator, or severe-defect count.

### Paired cluster bootstrap

Analysis first computes one baseline mean and one treatment mean per task, then derives task-level paired differences. Every task must contain both conditions. Bootstrap samples task differences with replacement and preserves duplicates. Point estimate equals mean task-level difference; percentile bounds use sampled paired means.

### Prompt interaction

Interaction test compares treatment-minus-baseline effects across prompt variants. API gains explicit `baseline`, `treatment`, and `alpha` inputs. Function requires paired observations for at least two variants, computes variant effect spread, and uses permutation testing over condition labels within task-variant pairs. `blocks_claim` becomes true when permutation p-value is below alpha. Seed parameter guarantees reproducibility.

### Test discovery

Pytest configuration sets `testpaths = ["tests"]`. Explicit archived or hidden-suite invocations remain possible by path.

## Error handling

All invalid study inputs, incomplete pairs, missing artifact sources, symlinks, and unusable interaction datasets raise `ContractError` with input-specific messages. CLI catches `ContractError`, writes error to stderr, and returns 1. No workflow reports success after skipping required evidence.

## Verification

Each defect receives regression test written before production change. Final gates:

- `.venv/bin/python -m compileall -q src`
- `.venv/bin/python -m pytest -q`
- `.venv/bin/python -m pytest tests --cov=src/tdd_ablation --cov-report=term-missing -q`
- CLI validation and report smoke tests against `study/`

