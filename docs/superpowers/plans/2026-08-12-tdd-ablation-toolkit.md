# TDD Ablation Toolkit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Do not dispatch subagents unless user explicitly authorizes delegation.

**Goal:** Build reproducible command-line toolkit that registers manually generated coding runs, evaluates them against hidden tests, and estimates quality and cost effects for eight engineering-process conditions.

**Architecture:** Python 3.12 package owns immutable JSON contracts, randomized schedules, artifact hashing, container-isolated evaluation, mutation-result ingestion, reliability checks, and deterministic analysis. CLI composes these modules without embedding experiment logic. Hidden tests remain outside submitted solution workspaces.

**Tech Stack:** Python 3.12.5, standard library, `pytest==8.3.2`, `pytest-cov==5.0.0`, `mutmut==3.6.0`, Docker or Podman CLI, JSON and CSV artifacts.

## Global Constraints

- Compare conditions `1`, `2`, `3`, `4`, `5`, `6a`, `6b`, and `6c`.
- Use 12 screening tasks, three prompt variants, and at least six repetitions per task-condition cell (protocol minimum; final count comes from the frozen power analysis).
- Use one shared token ceiling established by excluded pilot runs.
- Treat timeouts and budget exhaustion as incomplete outcomes in primary intention-to-treat analysis.
- Keep hidden evaluators outside agent-visible workspaces.
- Execute generated code with network disabled, read-only root filesystem, bounded CPU, bounded memory, and bounded process count.
- Pin Python patch release, dependency versions, container image digest, commands, timeouts, and environment variables.
- Produce identical outputs for identical inputs and analysis seed.
- Do not count copied artifacts as independent observations.
- Do not add agent API integration, hosted UI, provider comparison, or coding-agent orchestration.

---

### Task 1: Package Skeleton and JSON Contracts

**Files:**

- Create: `pyproject.toml`
- Create: `src/tdd_ablation/__init__.py`
- Create: `src/tdd_ablation/contracts.py`
- Create: `tests/test_contracts.py`

**Interfaces:**

- Produces: `load_json(path: Path) -> dict[str, object]`
- Produces: `require_fields(data, required, context) -> None`
- Produces: `validate_identifier(value: str, field: str) -> str`
- Produces: `ContractError(ValueError)`

- [ ] **Step 1: Write failing contract tests**

```python
def test_require_fields_reports_missing_names():
    with pytest.raises(ContractError, match="run: missing fields: task_id, condition_id"):
        require_fields({}, {"task_id", "condition_id"}, "run")

def test_identifier_rejects_path_escape():
    with pytest.raises(ContractError, match="condition_id"):
        validate_identifier("../6a", "condition_id")
```

- [ ] **Step 2: Run tests and verify expected failures**

Run: `python3.12 -m pytest tests/test_contracts.py -q`

Expected: collection fails because `tdd_ablation.contracts` does not exist.

- [ ] **Step 3: Add package metadata and minimal contract functions**

`pyproject.toml` must pin Python `==3.12.*`, expose `tdd-ablation = "tdd_ablation.cli:main"`, define dev dependencies listed in Tech Stack, and register the `container` pytest marker so the gated smoke test emits no unknown-marker warnings.

- [ ] **Step 4: Run focused tests**

Run: `python3.12 -m pytest tests/test_contracts.py -q`

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/tdd_ablation tests/test_contracts.py
git commit -m "feat: add study data contracts"
```

### Task 2: Pre-registration and Power Analysis

**Files:**

- Create: `src/tdd_ablation/preregistration.py`
- Create: `tests/test_preregistration.py`
- Create: `study/preregistration.example.json`

**Interfaces:**

- Consumes: contract helpers from Task 1
- Produces: `validate_preregistration(data: dict[str, object]) -> None`
- Produces: `required_runs(effect: float, standard_deviation: float, alpha: float, power: float, design_effect: float, attrition: float) -> int`

- [ ] **Step 1: Write failing tests for power and frozen criteria**

```python
def test_power_calculation_inflates_for_clustering_and_attrition():
    baseline = required_runs(0.05, 0.10, 0.05, 0.80, 1.0, 0.0)
    adjusted = required_runs(0.05, 0.10, 0.05, 0.80, 1.5, 0.10)
    assert adjusted > baseline

def test_preregistration_requires_confirmatory_success_rule():
    with pytest.raises(ContractError, match="confirmation_success"):
        validate_preregistration({"hypotheses": []})
```

- [ ] **Step 2: Verify red**

Run: `python3.12 -m pytest tests/test_preregistration.py -q`

Expected: import failure for missing module.

- [ ] **Step 3: Implement normal-approximation power calculation**

Use `statistics.NormalDist.inv_cdf`. Round upward after applying design effect and attrition. Reject non-positive effects, invalid probabilities, and attrition at or above one.

- [ ] **Step 4: Add example pre-registration**

Include eight hypotheses, alpha `0.05`, power `0.80`, five-point effect threshold, severe-defect risk-ratio ceiling `1.10`, 12 unseen tasks, 12 paired repetitions, and economic success rule.

- [ ] **Step 5: Run tests and commit**

```bash
python3.12 -m pytest tests/test_preregistration.py -q
git add src/tdd_ablation/preregistration.py tests/test_preregistration.py study/preregistration.example.json
git commit -m "feat: validate preregistration and power"
```

### Task 3: Condition Prompts and Prompt Sensitivity

**Files:**

- Create: `src/tdd_ablation/prompts.py`
- Create: `tests/test_prompts.py`
- Create: `study/prompts/conditions.json`

**Interfaces:**

- Produces: `validate_prompt_registry(data: dict[str, object]) -> None`
- Produces: `prompt_hash(text: str) -> str`
- Produces: `resolve_prompt(condition_id: str, variant_id: str) -> str`

- [ ] **Step 1: Write failing registry tests**

```python
def test_every_condition_has_three_distinct_variants(registry):
    validate_prompt_registry(registry)
    assert all(len(c["variants"]) == 3 for c in registry["conditions"])

def test_duplicate_prompt_text_is_rejected(registry):
    registry["conditions"][0]["variants"][1]["text"] = registry["conditions"][0]["variants"][0]["text"]
    with pytest.raises(ContractError, match="duplicate prompt hash"):
        validate_prompt_registry(registry)
```

- [ ] **Step 2: Verify red**

Run: `python3.12 -m pytest tests/test_prompts.py -q`

Expected: import failure.

- [ ] **Step 3: Implement registry validation and hashing**

Require exact condition set, variant IDs `v1` to `v3`, obligation checklist, prohibition checklist, completion criteria, and SHA-256 hash.

- [ ] **Step 4: Author 24 prompt variants**

Keep obligations identical within each condition. Change sentence order and wording only. Store explicit checklist beside each variant so review can detect accidental semantic drift.

- [ ] **Step 5: Run tests and commit**

```bash
python3.12 -m pytest tests/test_prompts.py -q
git add src/tdd_ablation/prompts.py tests/test_prompts.py study/prompts/conditions.json
git commit -m "feat: register process prompt variants"
```

### Task 4: Task Manifests and Severity Calibration

**Files:**

- Create: `src/tdd_ablation/tasks.py`
- Create: `src/tdd_ablation/reliability.py`
- Create: `tests/test_tasks.py`
- Create: `tests/test_reliability.py`
- Create: `study/tasks/task.example.json`

**Interfaces:**

- Produces: `validate_task_manifest(data: dict[str, object]) -> None`
- Produces: `weighted_kappa(left: list[int], right: list[int]) -> float`
- Produces: `validate_severity_calibration(ratings: dict[str, list[int]]) -> float`

- [ ] **Step 1: Write failing tests**

```python
def test_severity_calibration_requires_point_eight_agreement():
    with pytest.raises(ContractError, match="below 0.80"):
        validate_severity_calibration({"reviewer_a": [0, 1, 2], "reviewer_b": [3, 2, 1]})

def test_task_requires_frozen_hidden_test_mapping(task_manifest):
    del task_manifest["hidden_tests"]
    with pytest.raises(ContractError, match="hidden_tests"):
        validate_task_manifest(task_manifest)
```

- [ ] **Step 2: Verify red**

Run: `python3.12 -m pytest tests/test_tasks.py tests/test_reliability.py -q`

Expected: missing-module failures.

- [ ] **Step 3: Implement ordinal reliability and manifest checks**

Map low, medium, high, critical to `0..3`. Require two reviewers, 10 seeded defects, kappa at least `0.80`, adjudication record, frozen weights, business-behavior mapping, container digest, evaluator command, and mutation settings.

- [ ] **Step 4: Add complete example task manifest**

Include public spec path, hidden evaluator path, severity rubric version, dependency lock hash, Python patch version, Docker image digest, CPU, memory, process, network, and timeout controls.

- [ ] **Step 5: Run tests and commit**

```bash
python3.12 -m pytest tests/test_tasks.py tests/test_reliability.py -q
git add src/tdd_ablation/tasks.py src/tdd_ablation/reliability.py tests/test_tasks.py tests/test_reliability.py study/tasks/task.example.json
git commit -m "feat: validate tasks and severity calibration"
```

### Task 5: Randomized Screening and Confirmation Schedules

**Files:**

- Create: `src/tdd_ablation/schedule.py`
- Create: `tests/test_schedule.py`

**Interfaces:**

- Produces: `build_screening_schedule(task_ids: list[str], seed: int, repetitions: int = 6) -> list[ScheduleRow]`
- Produces: `build_confirmation_schedule(task_ids: list[str], condition_pairs: list[tuple[str, str]], seed: int, repetitions: int = 12) -> list[ScheduleRow]`
- Produces: `write_schedule(rows, path: Path) -> None`

- [ ] **Step 1: Write failing balance and determinism tests**

```python
def test_screening_schedule_default_repetitions_yield_576_balanced_rows():
    rows = build_screening_schedule([f"task-{i:02d}" for i in range(1, 13)], seed=17)
    assert len(rows) == 576
    assert set(Counter((r.task_id, r.condition_id, r.variant_id) for r in rows).values()) == {2}

def test_repetitions_scale_row_count_and_stay_balanced():
    rows = build_screening_schedule(TASKS, seed=17, repetitions=9)
    assert len(rows) == 864
    assert set(Counter((r.task_id, r.condition_id, r.variant_id) for r in rows).values()) == {3}

def test_repetitions_not_divisible_by_variants_are_rejected():
    with pytest.raises(ContractError, match="repetitions"):
        build_screening_schedule(TASKS, seed=17, repetitions=7)

def test_same_seed_produces_same_order():
    assert build_screening_schedule(TASKS, 17) == build_screening_schedule(TASKS, 17)
```

- [ ] **Step 2: Verify red**

Run: `python3.12 -m pytest tests/test_schedule.py -q`

Expected: missing-module failure.

- [ ] **Step 3: Implement balanced randomized schedule**

Use local `random.Random(seed)`. Assign immutable run ID, phase, order, task, condition, baseline condition when applicable, variant, repetition, and seed. Repetitions must divide evenly across the three prompt variants; reject counts that do not. Defaults (6 screening, 12 confirmation) are protocol minimums — the CLI passes the final power-derived repetition count from Task 15, which may be larger.

- [ ] **Step 4: Run tests and commit**

```bash
python3.12 -m pytest tests/test_schedule.py -q
git add src/tdd_ablation/schedule.py tests/test_schedule.py
git commit -m "feat: generate balanced run schedules"
```

### Task 6: Budget Pilot and Censoring Rules

**Files:**

- Create: `src/tdd_ablation/budget.py`
- Create: `tests/test_budget.py`

**Interfaces:**

- Produces: `shared_token_ceiling(pilot_runs: list[PilotRun], provider_limit: int) -> int`
- Produces: `censoring_report(runs: list[RunRecord]) -> CensoringReport`

- [ ] **Step 1: Write failing protocol tests**

```python
def test_shared_ceiling_uses_largest_condition_p95_plus_margin():
    ceiling = shared_token_ceiling(PILOT_RUNS, provider_limit=200_000)
    assert ceiling == 120_000

def test_protocol_review_triggers_above_ten_percent():
    report = censoring_report(make_runs(total=20, censored=3, condition="5"))
    assert report.requires_protocol_review is True

def test_ceiling_rejects_fewer_than_twelve_pilot_runs_per_condition():
    with pytest.raises(ContractError, match="12 pilot runs"):
        shared_token_ceiling(THIN_PILOT_RUNS, provider_limit=200_000)
```

- [ ] **Step 2: Verify red**

Run: `python3.12 -m pytest tests/test_budget.py -q`

Expected: missing-module failure.

- [ ] **Step 3: Implement nearest-rank percentile, margin, cap, and condition report**

Pilot inputs must carry `excluded_from_analysis=true`. Ceiling cannot vary by condition. Censored statuses are `token_exhausted` and `timed_out`. Require at least 12 pilot runs per condition — nearest-rank p95 over fewer samples degenerates to the maximum and produces an unstable ceiling. Record per-condition sample counts in the ceiling output.

- [ ] **Step 4: Run tests and commit**

```bash
python3.12 -m pytest tests/test_budget.py -q
git add src/tdd_ablation/budget.py tests/test_budget.py
git commit -m "feat: enforce shared budget protocol"
```

### Task 7: Immutable Run Import

**Files:**

- Create: `src/tdd_ablation/runs.py`
- Create: `src/tdd_ablation/hashing.py`
- Create: `tests/test_runs.py`

**Interfaces:**

- Produces: `hash_tree(root: Path) -> str`
- Produces: `import_run(schedule_row: ScheduleRow, source: Path, metadata: dict[str, object], store: Path, duplicate_attestation: DuplicateAttestation | None = None) -> RunRecord`
- Produces: `verify_store(store: Path) -> list[str]`

- [ ] **Step 1: Write failing immutability tests**

```python
def test_import_rejects_duplicate_artifact_without_attestation(tmp_path):
    first = import_run(ROW_A, SOURCE, META, tmp_path)
    with pytest.raises(ContractError, match=first.artifact_hash):
        import_run(ROW_B, SOURCE, META, tmp_path)

def test_attested_duplicate_imports_and_is_flagged(tmp_path):
    import_run(ROW_A, SOURCE, META, tmp_path)
    record = import_run(ROW_B, SOURCE, META, tmp_path, duplicate_attestation=ATTESTATION)
    assert record.duplicate_of == ROW_A.run_id
    assert record.attestation.reviewer_ids == ATTESTATION.reviewer_ids

def test_verify_store_detects_changed_file(tmp_path):
    record = import_run(ROW_A, SOURCE, META, tmp_path)
    (record.artifact_path / "solution.py").write_text("changed")
    assert verify_store(tmp_path) == [record.run_id]
```

- [ ] **Step 2: Verify red**

Run: `python3.12 -m pytest tests/test_runs.py -q`

Expected: missing-module failure.

- [ ] **Step 3: Implement canonical hashing and copy-on-import**

Hash normalized relative paths plus file bytes. Reject symlinks, path escapes, and duplicate run IDs. Reject duplicate artifact hashes by default; identical independent solutions are plausible on small tasks, so accept a duplicate only with a `DuplicateAttestation` (two reviewer IDs, session evidence paths, rationale) recorded in the run manifest and flagged `duplicate_of` for the analysis report. Write manifest last with atomic rename. Never modify imported artifacts.

- [ ] **Step 4: Run tests and commit**

```bash
python3.12 -m pytest tests/test_runs.py -q
git add src/tdd_ablation/runs.py src/tdd_ablation/hashing.py tests/test_runs.py
git commit -m "feat: import immutable run artifacts"
```

### Task 8: Container-Isolated Hidden Evaluation

**Files:**

- Create: `src/tdd_ablation/container.py`
- Create: `src/tdd_ablation/evaluate.py`
- Create: `tests/test_container.py`
- Create: `tests/test_evaluate.py`

**Interfaces:**

- Produces: `build_container_command(task: TaskManifest, run: RunRecord, output: Path) -> list[str]`
- Produces: `evaluate_run(task, run, output, runner=subprocess.run) -> EvaluationRecord`
- Produces: `parse_junit(path: Path, severity_map: dict[str, str]) -> HiddenTestResult`

- [ ] **Step 1: Write failing isolation test**

```python
def test_container_command_applies_security_limits(task, run, output):
    command = build_container_command(task, run, output)
    joined = " ".join(command)
    assert "--network none" in joined
    assert "--read-only" in joined
    assert "--cap-drop ALL" in joined
    assert "--pids-limit" in joined
    assert "no-new-privileges" in joined
```

- [ ] **Step 2: Write failing JUnit scoring test**

```python
def test_critical_failure_has_frozen_weight(tmp_path):
    result = parse_junit(write_fixture(tmp_path, "critical_failure.xml"), {"test_no_data_loss": "critical"})
    assert result.failed_weight == 8
```

- [ ] **Step 3: Verify red**

Run: `python3.12 -m pytest tests/test_container.py tests/test_evaluate.py -q`

Expected: missing-module failures.

- [ ] **Step 4: Implement runtime-neutral command builder**

Accept only `docker` or `podman`. Mount solution read-only, hidden evaluator read-only, and output directory writable. Apply task-pinned image digest, CPU, memory, process, timeout, and environment settings. Disable network and all capabilities. Return structured timeout, collection failure, and test outcomes.

- [ ] **Step 5: Run unit tests and gated container smoke test**

Run: `python3.12 -m pytest tests/test_container.py tests/test_evaluate.py -q`

Run when container runtime exists: `RUN_CONTAINER_TESTS=1 python3.12 -m pytest tests/test_evaluate.py -m container -q`

- [ ] **Step 6: Commit**

```bash
git add src/tdd_ablation/container.py src/tdd_ablation/evaluate.py tests/test_container.py tests/test_evaluate.py
git commit -m "feat: evaluate submissions in locked containers"
```

### Task 9: Mutation Protocol and Result Ingestion

**Files:**

- Create: `src/tdd_ablation/mutation.py`
- Create: `tests/test_mutation.py`
- Create: `study/mutation-protocol.json`

**Interfaces:**

- Produces: `validate_mutation_protocol(data: dict[str, object]) -> None`
- Produces: `parse_mutation_results(path: Path) -> MutationResult`
- Produces: `mutation_score(result: MutationResult, exclude_equivalent: bool = False) -> float`

- [ ] **Step 0: Verify mutmut 3.6.0 export capability (spike)**

Before pinning the protocol, confirm mutmut `3.6.0` can produce per-mutant ID, location, diff, operator class, result, and duration. mutmut 3.x changed its cache and browse model versus 2.x and has no rich native JSON export; if fields are missing, write a small extraction wrapper that reads mutmut's result cache and emits the required JSON, and pin that wrapper's behavior with a fixture test. Record the chosen extraction path in `study/mutation-protocol.json`. If mutmut 3.6.0 cannot yield the required fields even via its cache, stop and revise the plan's mutation tooling before proceeding.

- [ ] **Step 1: Write failing denominator tests**

```python
def test_primary_denominator_keeps_timeouts_suspicious_and_equivalents():
    result = MutationResult(killed=8, survived=1, suspicious=1, timed_out=1, equivalent=1)
    assert mutation_score(result) == pytest.approx(8 / 12)

def test_import_failure_invalidates_mutation_run():
    with pytest.raises(ContractError, match="collection failure"):
        parse_mutation_results(FIXTURES / "collection-failed.json")
```

- [ ] **Step 2: Verify red**

Run: `python3.12 -m pytest tests/test_mutation.py -q`

Expected: missing-module failure.

- [ ] **Step 3: Pin operator-level protocol**

Protocol records Python `3.12.5`, `mutmut==3.6.0`, full unfiltered operator set, source paths, submitted test command, baseline timeout, mutant timeout multiplier, worker count, environment, coverage filtering disabled, type-check filtering disabled, and repository tag `3.6.0`. Export every mutant ID, location, diff, operator class, result, and duration.

- [ ] **Step 4: Implement parser and primary/sensitivity scores**

Primary denominator includes every generated mutant. Sensitivity score excludes only equivalents independently classified by two blind reviewers and recorded in adjudication file.

- [ ] **Step 5: Run tests and commit**

```bash
python3.12 -m pytest tests/test_mutation.py -q
git add src/tdd_ablation/mutation.py tests/test_mutation.py study/mutation-protocol.json
git commit -m "feat: pin mutation protocol and scoring"
```

### Task 10: Blind Review Reliability

**Files:**

- Modify: `src/tdd_ablation/reliability.py`
- Create: `src/tdd_ablation/reviews.py`
- Create: `tests/test_reviews.py`
- Create: `study/review-rubric.json`

**Interfaces:**

- Produces: `prepare_blind_review(run: RunRecord, destination: Path) -> ReviewPacket`
- Produces: `review_reliability(reviews: list[Review]) -> ReliabilityResult`
- Produces: `validate_review_panel(result: ReliabilityResult) -> None`

- [ ] **Step 1: Write failing blinding and threshold tests**

```python
def test_review_packet_excludes_condition_and_trace(tmp_path):
    packet = prepare_blind_review(RUN, tmp_path)
    manifest = json.loads(packet.manifest_path.read_text())
    assert collect_keys(manifest).isdisjoint({"condition_id", "variant_id", "prompt_text", "conversation_log"})
    assert not any(packet.artifact_path.rglob("conversation*"))

def test_low_reliability_requires_full_rescore():
    with pytest.raises(ContractError, match="full independent rescoring"):
        validate_review_panel(ReliabilityResult(metric="weighted_kappa", value=0.62))
```

- [ ] **Step 2: Verify red**

Run: `python3.12 -m pytest tests/test_reviews.py -q`

Expected: missing-module failure.

- [ ] **Step 3: Implement blind packet creation and agreement checks**

Two-reviewer panels use weighted Cohen's kappa. Larger panels use Krippendorff's alpha. Require `0.70`; preserve original scores, recalibration version, rescored values, and adjudication.

- [ ] **Step 4: Run tests and commit**

```bash
python3.12 -m pytest tests/test_reviews.py tests/test_reliability.py -q
git add src/tdd_ablation/reliability.py src/tdd_ablation/reviews.py tests/test_reviews.py study/review-rubric.json
git commit -m "feat: enforce blind review reliability"
```

### Task 11: Effect Estimates and Confirmation Decisions

**Files:**

- Create: `src/tdd_ablation/analysis.py`
- Create: `tests/test_analysis.py`

**Interfaces:**

- Produces: `paired_effect(rows: list[AnalysisRow], baseline: str, treatment: str, seed: int) -> EffectEstimate`
- Produces: `prompt_interaction(rows: list[AnalysisRow]) -> InteractionResult`
- Produces: `confirmation_decision(effect: EffectEstimate, defects: RiskRatioEstimate, economics: EffectEstimate, censoring: CensoringReport, interaction: InteractionResult, completed_runs: int, required_runs: int) -> Decision`

- [ ] **Step 1: Write failing decision tests**

```python
def test_confirmation_requires_all_seven_criteria():
    decision = confirmation_decision(
        effect=EffectEstimate(point=0.06, low=0.01, high=0.11),
        defects=RiskRatioEstimate(point=0.90, low=0.70, high=1.05),
        economics=EffectEstimate(point=100, low=10, high=190),
        censoring=ACCEPTABLE_CENSORING,
        interaction=NO_BLOCKING_INTERACTION,
        completed_runs=144,
        required_runs=144,
    )
    assert decision.adopt is True

def test_blocking_prompt_interaction_forces_rejection():
    decision = confirmation_decision(
        effect=STRONG_EFFECT, defects=SAFE_DEFECTS, economics=POSITIVE_ECONOMICS,
        censoring=ACCEPTABLE_CENSORING, interaction=BLOCKING_INTERACTION,
        completed_runs=144, required_runs=144,
    )
    assert decision.adopt is False
    assert "prompt interaction" in decision.reasons[0]

def test_underpowered_sample_forces_rejection():
    decision = confirmation_decision(
        effect=STRONG_EFFECT, defects=SAFE_DEFECTS, economics=POSITIVE_ECONOMICS,
        censoring=ACCEPTABLE_CENSORING, interaction=NO_BLOCKING_INTERACTION,
        completed_runs=120, required_runs=144,
    )
    assert decision.adopt is False

def test_prompt_interaction_blocks_broad_claim():
    assert prompt_interaction(PROMPT_SENSITIVE_ROWS).blocks_claim is True
```

- [ ] **Step 2: Verify red**

Run: `python3.12 -m pytest tests/test_analysis.py -q`

Expected: missing-module failure.

- [ ] **Step 3: Implement deterministic task-cluster bootstrap**

Resample tasks, then paired repetitions within task, using supplied seed. Report point estimate and percentile 95 percent interval. Score incomplete runs as zero for primary analysis. Produce secondary complete-case estimate. Keep prompt variant and condition-by-variant results separate.

- [ ] **Step 4: Implement confirmation rule**

Require effect interval above zero, point estimate at least `0.05`, severe-defect risk-ratio upper bound below `1.10`, positive economic lower bound, acceptable censoring, acceptable prompt interaction, and pre-registered sample size.

- [ ] **Step 5: Run tests and commit**

```bash
python3.12 -m pytest tests/test_analysis.py -q
git add src/tdd_ablation/analysis.py tests/test_analysis.py
git commit -m "feat: estimate effects and adoption decisions"
```

### Task 12: CLI, Reports, Reference Study, and Reproduction Proof

**Files:**

- Create: `src/tdd_ablation/cli.py`
- Create: `src/tdd_ablation/report.py`
- Create: `tests/test_cli.py`
- Create: `tests/test_end_to_end.py`
- Create: `study/README.md`
- Create: `study/tasks/README.md`
- Create: `study/hidden/README.md`
- Create: `README-ABLATION.md`

**Interfaces:**

- Produces CLI commands: `validate`, `schedule`, `budget`, `import-run`, `evaluate`, `mutation-import`, `review-pack`, `analyze`, `report`, `verify-store`
- Produces: `render_report(results: StudyResults) -> str`

- [ ] **Step 1: Write failing CLI workflow test**

```python
def test_reference_study_replays_identically(tmp_path):
    first = run_cli(["report", "--study", str(FIXTURE_STUDY), "--output", str(tmp_path / "one")])
    second = run_cli(["report", "--study", str(FIXTURE_STUDY), "--output", str(tmp_path / "two")])
    assert first.returncode == second.returncode == 0
    assert hash_tree(tmp_path / "one") == hash_tree(tmp_path / "two")
```

- [ ] **Step 2: Verify red**

Run: `python3.12 -m pytest tests/test_cli.py tests/test_end_to_end.py -q`

Expected: missing CLI module.

- [ ] **Step 3: Implement `argparse` CLI**

Each command returns non-zero on contract failure and writes machine-readable error JSON to stderr. No command changes imported artifacts. Report writes run CSV, condition CSV, prompt-sensitivity CSV, censoring CSV, mutation CSV, review-reliability CSV, decision JSON, and Markdown executive report.

- [ ] **Step 4: Add reference fixture and operator guide**

Guide covers preregistration, task freezing, hidden evaluator separation, severity calibration, prompt review, budget pilot, randomized schedule, manual coding sessions, artifact import, container evaluation, mutation run, blind review, analysis, confirmation, model update handling, and artifact verification.

- [ ] **Step 5: Run full verification**

```bash
python3.12 -m pytest -q
python3.12 -m pytest --cov=tdd_ablation --cov-branch --cov-report=term-missing
python3.12 -m tdd_ablation.cli validate --study tests/fixtures/reference-study
python3.12 -m tdd_ablation.cli verify-store --study tests/fixtures/reference-study
```

Expected: all tests pass, branch coverage at least 90 percent, fixture study validates, fixture store verifies, no warnings. Real `study/` directory validates only after Task 14 completes manifests; do not gate this task on it.

- [ ] **Step 6: Commit**

```bash
git add src/tdd_ablation/cli.py src/tdd_ablation/report.py tests/test_cli.py tests/test_end_to_end.py study README-ABLATION.md
git commit -m "feat: deliver reproducible ablation toolkit"
```

### Task 13: Author 12 Screening Tasks

**Files:**

- Create: `study/tasks/task-01.json` through `study/tasks/task-12.json`
- Create: `study/public/task-01.md` through `study/public/task-12.md`
- Create: `study/task-portfolio-review.md`
- Create: `tests/test_study_portfolio.py`

**Interfaces:**

- Consumes: task contract from Task 4
- Produces: two tasks each for parsing, state transitions, concurrency, API contracts, transformations, and defect repair

- [ ] **Step 1: Write portfolio acceptance test**

```python
def test_screening_portfolio_has_two_tasks_per_family():
    tasks = load_tasks(Path("study/tasks"))
    assert len(tasks) == 12
    assert Counter(task.family for task in tasks) == {
        "parsing": 2,
        "state": 2,
        "concurrency": 2,
        "api": 2,
        "transformation": 2,
        "defect_repair": 2,
    }
```

- [ ] **Step 2: Verify red**

Run: `python3.12 -m pytest tests/test_study_portfolio.py -q`

Expected: failure showing 12 missing task manifests.

- [ ] **Step 3: Author public tasks and draft manifests**

Each task targets 2 to 4 engineer-hours without agent assistance, exposes explicit public contract, avoids external services, uses pinned dependencies, and contains at least one state or boundary interaction not reducible to line coverage. Draft manifests carry everything except the `hidden_tests` mapping, which Task 14 adds — do not run full `cli validate` yet; it requires `hidden_tests` and passes only after Task 14. `load_tasks` accepts a `draft=True` flag that defers hidden-test validation; the portfolio test uses it.

- [ ] **Step 4: Conduct blind difficulty review**

Three reviewers estimate effort and identify ambiguity without seeing process conditions or hidden tests. Revise tasks until every requirement has one interpretation and median effort stays within target band. Freeze public-spec hashes only; manifest hashes freeze at the end of Task 14 once hidden evaluators exist.

- [ ] **Step 5: Validate portfolio and commit**

```bash
python3.12 -m pytest tests/test_study_portfolio.py -q
git add study/tasks study/public study/task-portfolio-review.md tests/test_study_portfolio.py
git commit -m "study: freeze public screening specs"
```

### Task 14: Build Hidden Evaluators and Seeded Defects

**Files:**

- Create: `study/hidden/task-01/` through `study/hidden/task-12/`
- Create: `study/calibration/seeded-defects.json`
- Create: `study/calibration/severity-ratings.csv`
- Create: `study/calibration/severity-adjudication.json`
- Create: `tests/test_hidden_catalog.py`

**Interfaces:**

- Consumes: frozen public tasks from Task 13
- Produces: deterministic hidden tests, adversarial tests, seeded calibration defects, frozen severity weights

- [ ] **Step 1: Add hidden-evaluator contract tests**

```python
def test_every_hidden_test_has_business_behavior_and_severity():
    for task in load_tasks(Path("study/tasks")):
        observed = collect_hidden_nodeids(task.hidden_evaluator_path)
        assert observed == set(task.hidden_tests)
        assert all(item.business_behavior for item in task.hidden_tests.values())
```

- [ ] **Step 2: Verify red**

Run: `python3.12 -m pytest tests/test_hidden_catalog.py -q`

Expected: failure because hidden evaluators do not exist.

- [ ] **Step 3: Write evaluator before any coding-agent run**

Cover nominal behavior, malformed input, boundary values, cross-operation state, and specified failure semantics. Include critical or high cases only where business-impact rubric warrants them. Run evaluator against reference implementation and deliberately broken implementations.

- [ ] **Step 4: Complete task manifests with hidden-test mappings**

Add the `hidden_tests` mapping (node ID, business behavior, severity) to each draft manifest from Task 13. Public-spec hashes frozen in Task 13 must not change; only manifest fields describing hidden evaluators may be added.

- [ ] **Step 5: Calibrate severity**

Two domain reviewers independently score 10 seeded defects. Require weighted kappa at least `0.80`; adjudicate, freeze labels, and record all changes. If threshold fails, revise rubric and repeat full calibration before proceeding.

- [ ] **Step 6: Validate, freeze, and commit manifest and evaluator hashes**

```bash
python3.12 -m tdd_ablation.cli validate --study study
```

Freeze manifest hashes now. Commit only encrypted hidden package or access-controlled submodule pointer when coding agents can access repository. Commit hashes, catalog, and calibration evidence in main study repository.

### Task 15: Freeze Pre-registration, Prompts, and Power

**Files:**

- Create: `study/preregistration.json`
- Modify: `study/prompts/conditions.json`
- Create: `study/power-analysis.json`
- Create: `study/prompt-equivalence-review.csv`

**Interfaces:**

- Consumes: frozen tasks and hidden-test variance estimates from author-only dry runs
- Produces: signed study protocol and final run counts

- [ ] **Step 1: Complete hypothesis registry**

For each hypothesis, record matched conditions, primary outcome, direction, minimum useful effect, alpha, power, cluster assumptions, attrition, analysis model, multiplicity treatment, and confirmation rule. Also record the screening and confirmation schedule seeds — Task 17 and Task 18 must read seeds from the pre-registration, not invent them at run time.

- [ ] **Step 2: Review prompt equivalence**

Two reviewers compare three variants within each condition against obligation and prohibition checklists. Any semantic disagreement blocks freezing until rewritten and re-reviewed.

- [ ] **Step 3: Calculate power and final sample sizes**

Run: `python3.12 -m tdd_ablation.cli validate --study study`

Store executable inputs and outputs. Final count equals larger of protocol minimum and calculated requirement. Record the resulting per-cell repetition count in `study/power-analysis.json`; the `schedule` CLI command reads it and passes it as the `repetitions` argument.

- [ ] **Step 4: Freeze hashes and commit**

```bash
git add study/preregistration.json study/prompts/conditions.json study/power-analysis.json study/prompt-equivalence-review.csv
git commit -m "study: preregister ablation experiment"
```

No changes after this commit except versioned protocol deviation approved before unblinding.

### Task 16: Run Excluded Budget Pilot

**Files:**

- Create: `study/pilot/schedule.csv`
- Create: `study/pilot/runs/`
- Create: `study/pilot/budget-decision.json`

**Interfaces:**

- Consumes: frozen tasks and prompts
- Produces: shared token ceiling and timeout used by all main-study conditions

- [ ] **Step 1: Generate balanced pilot schedule**

Use at least four tasks spanning difficulty bands and three runs per task-condition cell, giving at least 12 runs per condition — the floor `shared_token_ceiling` enforces. Mark every pilot row `excluded_from_analysis=true`.

- [ ] **Step 2: Execute pilot in randomized order**

Capture full metadata and failures. Do not reuse pilot solutions in screening.

- [ ] **Step 3: Calculate shared ceiling**

Use largest condition-level token p95 plus 20 percent, capped by provider limit. Set shared timeout from same non-differential rule. Document provider limit and any cap.

- [ ] **Step 4: Freeze pilot decision**

```bash
python3.12 -m tdd_ablation.cli budget --study study --pilot study/pilot/runs --output study/pilot/budget-decision.json
git add study/pilot
git commit -m "study: freeze shared execution budget"
```

### Task 17: Execute and Audit Screening

**Files:**

- Create: `study/screening/schedule.csv`
- Create: `study/screening/runs/`
- Create: `study/screening/audit.json`
- Create: `study/screening/results/`

**Interfaces:**

- Consumes: frozen protocol, shared budget, 12 tasks, 24 prompts
- Produces: minimum 576 immutable run records and blinded evaluation results

- [ ] **Step 1: Generate schedule and verify balance**

```bash
python3.12 -m tdd_ablation.cli schedule --phase screening --study study --output study/screening/schedule.csv
```

Seed and repetition count come from `study/preregistration.json` and `study/power-analysis.json`; the command rejects ad-hoc seed overrides once the protocol is frozen. Require exact count from final power analysis, with equal variant allocation.

- [ ] **Step 2: Run coding sessions manually in scheduled order**

Use fresh workspace per row. Record unsuccessful, timed-out, and budget-exhausted attempts. Never substitute unrecorded rerun.

- [ ] **Step 3: Import and verify every artifact**

```bash
python3.12 -m tdd_ablation.cli verify-store --study study/screening
```

- [ ] **Step 4: Run hidden evaluation and mutation protocol**

Keep condition labels inaccessible to reviewers. Audit container settings and task hashes before each evaluation batch.

- [ ] **Step 5: Stop on protocol breach**

Pause study if censoring exceeds 10 percent in any condition, model version changes, hashes drift, evaluator collection fails, or duplicate artifact appears. Record deviation before resuming.

- [ ] **Step 6: Analyze screening without changing frozen criteria**

Promote only pre-registered matched comparisons meeting screening rule. Report prompt interactions, censoring, task heterogeneity, mutation scores, and cost separately.

### Task 18: Execute Confirmation and Publish Decision

**Files:**

- Create: `study/confirmation/tasks/`
- Create: `study/confirmation/schedule.csv`
- Create: `study/confirmation/runs/`
- Create: `study/confirmation/results/`
- Create: `study/reports/final.md`
- Create: `study/reports/reproduction.json`

**Interfaces:**

- Consumes: promoted screening comparisons and 12 unseen tasks
- Produces: confirmation decisions and economic adoption recommendation

- [ ] **Step 1: Author and freeze 12 unseen tasks**

Use same family balance, difficulty review, hidden-evaluator process, severity calibration, and hashing rules as screening. No screening task or domain story may be copied.

- [ ] **Step 2: Generate paired confirmation schedule**

Require at least 144 runs per condition, four repetitions per prompt variant, or larger power-derived count.

- [ ] **Step 3: Execute, evaluate, mutate, and review**

Apply unchanged model, prompts, budget, environment, scoring, and blinding. Provider model update pauses execution or creates separate version stratum.

- [ ] **Step 4: Apply frozen confirmation rule**

Adopt only when quality interval excludes zero, point estimate reaches five percentage points, severe-defect risk-ratio upper bound remains below `1.10`, economic lower bound stays positive, censoring stays acceptable, and prompt interaction does not block claim.

- [ ] **Step 5: Reproduce outputs twice**

```bash
python3.12 -m tdd_ablation.cli report --study study --output study/reports/run-one
python3.12 -m tdd_ablation.cli report --study study --output study/reports/run-two
```

Require identical tree hashes. Publish deviations, null findings, failed hypotheses, confidence intervals, raw run manifests, and model-version scope.

## Final Acceptance Gate

- [ ] `git status --short` shows no unexpected files.
- [ ] Fresh Python 3.12 environment installs from pinned project metadata.
- [ ] Full unit and integration suite passes twice.
- [ ] Container smoke test passes on supported runtime.
- [ ] Reference report hashes match across repeated runs.
- [ ] Imported artifact mutation causes store verification failure.
- [ ] Eight conditions and 24 prompt variants validate.
- [ ] Screening schedule row count matches frozen power analysis (minimum 576) with balanced cells and variants.
- [ ] Confirmation schedule matches frozen power analysis (minimum 12 repetitions per task-condition cell, four per prompt variant).
- [ ] Primary analysis retains censored runs and all generated mutants.
- [ ] Duplicate artifact imports without attestation fail; attested duplicates carry `duplicate_of` and reviewer evidence.
- [ ] Low severity agreement or design-review agreement blocks study progression.
- [ ] Prompt interaction, censoring, sample-size, quality, safety, or economic failure blocks adoption claim.
- [ ] No agent runner, hosted UI, or provider-specific orchestration shipped.
