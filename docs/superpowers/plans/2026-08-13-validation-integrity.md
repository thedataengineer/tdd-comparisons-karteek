# Validation Integrity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make validation, review, scoring, analysis, and reporting fail closed when required evidence is missing or misclassified.

**Architecture:** Keep existing module boundaries. Strengthen inputs and calculations at each responsible function, then configure pytest to isolate product tests from archived experimental suites.

**Tech Stack:** Python 3.12, pytest 8.3.2, pytest-cov 5.0.0, standard library only

**Spec:** `docs/superpowers/specs/2026-08-12-validation-integrity-design.md`

## Global Constraints

- Preserve public APIs unless spec explicitly changes one.
- Add no runtime or development dependencies.
- Write each regression test before changing production code.
- Do not modify archived solution directories or hidden evaluator files.

---

### Task 1: Fail-closed CLI inputs and data-backed reports

**Files:**
- Modify: `tests/test_cli.py`
- Modify: `src/tdd_ablation/cli.py`
- Create: `study/results.json`

**Interfaces:**
- Consumes: `load_json(path: Path) -> dict[str, Any]`, existing validators, `render_report(results)`
- Produces: `validate` and `report` commands returning 1 on missing or malformed required inputs

- [ ] Add tests proving missing study validation fails, missing registry fails, missing report results fail, and report renders literal fixture results.
- [ ] Run focused CLI tests and confirm failures come from current permissive or hard-coded behavior.
- [ ] Require study directory, `preregistration.json`, and `prompts/conditions.json` in validation path.
- [ ] Load and structurally validate `results.json` before rendering report.
- [ ] Add frozen `study/results.json` matching published final report.
- [ ] Run focused CLI and end-to-end tests.

### Task 2: Copy real artifacts into blind-review packets

**Files:**
- Modify: `tests/test_reviews.py`
- Modify: `src/tdd_ablation/reviews.py`

**Interfaces:**
- Consumes: `prepare_blind_review(run, destination, artifact_source)`
- Produces: packet containing copied source artifacts, no traces, logs, symlinks, or run metadata

- [ ] Add tests proving source content survives, nested files copy, traces are excluded, missing source fails, and symlinks fail.
- [ ] Run focused review tests and confirm signature or content failures.
- [ ] Validate artifact source and recursively copy allowlisted artifact content while excluding trace material.
- [ ] Build manifest artifact list from copied relative paths.
- [ ] Run focused review tests.

### Task 3: Score skipped JUnit cases correctly

**Files:**
- Modify: `tests/test_contracts.py` or evaluator-specific existing test file
- Modify: `src/tdd_ablation/evaluate.py`

**Interfaces:**
- Produces: `EvaluationRecord.skipped_count`; skipped tests excluded from score denominator

- [ ] Add test with passed, failed, and skipped cases using hand-calculated counts and weighted score.
- [ ] Run focused test and confirm skipped case currently inflates passed score.
- [ ] Detect `<skipped>` before pass/fail branches and increment `skipped_count` only.
- [ ] Run focused evaluator tests.

### Task 4: Preserve cluster multiplicity in paired bootstrap

**Files:**
- Modify: `tests/test_analysis.py`
- Modify: `src/tdd_ablation/analysis.py`

**Interfaces:**
- Consumes: task-paired baseline and treatment observations
- Produces: task-level mean effect and replacement bootstrap interval preserving repeated clusters

- [ ] Add deterministic skewed-task regression test expecting point `20.0` and upper bound `60.0` for seed and bootstrap count fixed by fixture.
- [ ] Add incomplete-pair rejection test.
- [ ] Run focused tests and confirm old membership sampling fails.
- [ ] Compute per-task paired means, reject missing pairs, sample task effects by index with replacement.
- [ ] Run focused analysis tests.

### Task 5: Replace prompt-interaction stub

**Files:**
- Modify: `tests/test_analysis.py`
- Modify: `src/tdd_ablation/analysis.py`

**Interfaces:**
- Consumes: `prompt_interaction(rows, baseline, treatment, seed=0, alpha=0.05, num_permutations=1000)`
- Produces: reproducible permutation p-value and blocking flag

- [ ] Add no-interaction and material-interaction fixtures with literal expected blocking decisions.
- [ ] Add insufficient-variant rejection test.
- [ ] Run focused tests and confirm current constant result fails material-interaction case.
- [ ] Compute per-variant paired effects and observed spread.
- [ ] Permute condition assignment within paired task-variant observations; calculate corrected Monte Carlo p-value.
- [ ] Run focused analysis tests.

### Task 6: Restrict default pytest discovery

**Files:**
- Modify: `pyproject.toml`

**Interfaces:**
- Produces: default pytest collection limited to `tests/`

- [ ] Add `testpaths = ["tests"]` under pytest configuration.
- [ ] Run `.venv/bin/python -m pytest --collect-only -q`; confirm only product suite collects.
- [ ] Run default full suite.

### Task 7: Final verification

**Files:**
- Verify only

**Interfaces:**
- Produces: current evidence for syntax, tests, coverage, and CLI workflows

- [ ] Run `.venv/bin/python -m compileall -q src`.
- [ ] Run `.venv/bin/python -m pytest -q`.
- [ ] Run `.venv/bin/python -m pytest tests --cov=src/tdd_ablation --cov-report=term-missing -q`.
- [ ] Run CLI validate and report smoke tests using temporary output.
- [ ] Inspect `git diff --check` and scoped diff.
