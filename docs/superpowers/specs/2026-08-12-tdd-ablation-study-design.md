# TDD Practice Ablation Study Design

## Decision

Build staged randomized study that measures individual engineering practices instead of comparing broad “TDD” and “non-TDD” labels. Screening phase identifies practices with credible quality or cost effects. Confirmation phase retests selected practices against unseen tasks with frozen prompts.

Study produces evidence for process decisions, not universal claims about TDD. Each adoption decision uses hidden correctness, severe defect rate, execution cost, and human review cost.

## Claims Under Test

Study tests eight pre-registered hypotheses:

1. Requiring tests raises hidden-test pass rate.
2. Writing tests first outperforms writing tests after implementation.
3. Incremental red-green cycles outperform batched test-first work.
4. Mandatory refactoring checkpoints reduce design defects.
5. Upfront contract design reduces interface and error-model defects.
6. Line coverage predicts hidden correctness.
7. Mutation score predicts hidden correctness better than line coverage.
8. Quality gains offset added tokens, elapsed time, and review effort.

Each hypothesis must define metric, effect direction, minimum useful effect, sample size, and analysis rule before first run. [ASSUMPTION] Initial adoption threshold requires either five percentage points higher hidden-test score or 30 percent fewer high-severity defects.

## Experimental Conditions

Screening compares six conditions:

1. Task only
2. Tests required, timing unspecified
3. Tests written after implementation
4. Tests written first as batch
5. Incremental red-green cycles
6. Incremental red-green cycles with upfront contract design and mandatory refactoring checkpoints

All conditions receive identical task specification, environment, dependencies, completion budget, and tool permissions. Only process instruction changes. Conditions never include coverage targets because coverage requirements would confound testing practice with completion policy.

## Task Portfolio

Screening uses 12 tasks across parsing, state transitions, concurrency, API contracts, transformations, and defect repair. Tasks contain similar difficulty bands but different domain wording and implementation details.

Each task includes public requirements, hidden acceptance tests, adversarial cases, severity labels, and mutation configuration. Task author freezes hidden evaluation before any coding run begins.

## Run Protocol

Run every task-condition cell at least five times during screening. Randomize execution order. Create fresh isolated workspace for every run and never reuse generated code across conditions.

Pin model identifier, model settings, tool permissions, token budget, timeout, runtime, dependency versions, and hardware class. Record failed and timed-out runs instead of silently replacing them. Replacement runs receive separate identifiers and remain linked to original failures.

Store immutable run manifest containing condition ID, task ID, repetition, randomized order, model configuration, prompt hashes, source commit, timestamps, token counts, tool calls, exit state, and artifact hashes.

## Evaluation

Coding agent cannot access hidden evaluation artifacts. Deterministic checks provide primary evidence:

- Hidden functional tests
- Adversarial boundary tests
- Mutation testing against submitted tests
- API and dependency conformance checks
- Static checks for dead code and forbidden dependencies
- Human adjudication for disputed high-severity failures

Blind design review removes condition labels, prompt text, session traces, and naming clues. Model-based review remains secondary evidence. Generator and model judge cannot share identical model configuration for primary scoring.

Primary metric: severity-weighted hidden-test score. Secondary metrics include high-severity defect count, mutation score, authored-test effectiveness, tokens, elapsed time, tool calls, human review minutes, and implementation-to-test LOC ratio. Line coverage remains diagnostic data.

## Analysis

Analyze practice effects by task and across task families. Report effect sizes and confidence intervals, not rank alone. Treat each unique generation run as one observation; copied artifacts never count again.

Ablation interpretation:

- Testing need exists when tests-required condition beats task-only condition.
- Test-first need exists when batched test-first beats tests-after.
- Incremental-cycle need exists when red-green beats batched test-first enough to cover added cost.
- Contract and refactoring bundle earns confirmation when condition six beats condition five.
- Metric validity exists when metric predicts hidden correctness on unseen runs.

Confirmation uses new tasks, frozen prompts, at least 10 repetitions per promoted condition, and same evaluation rules. Failed confirmation rejects adoption claim.

## Economic Decision Rule

For each practice, calculate:

```text
expected value =
  avoided defect cost
  - agent execution cost
  - engineer review cost
  - workflow delay cost
```

Adopt practice only when lower confidence bound clears agreed business threshold. Report quality and cost separately before combining them, so stakeholders can replace assumed defect costs with their own values.

## Repository Outputs

Study repository contains:

- Pre-registration document
- Versioned condition prompts
- Task manifests and public specifications
- Hidden evaluator package stored outside agent workspaces
- Immutable run manifests and submitted artifacts
- Deterministic scoring command
- Statistical analysis command
- Generated comparison tables and charts
- Reproduction guide with pinned dependencies

## Non-Goals

First release excludes agent API integration, hosted dashboards, provider comparison, automatic coding-agent orchestration, and subjective prose-report generation. Operator runs coding sessions and supplies captured artifacts. Toolkit validates, scores, analyzes, and reports those artifacts.

## Acceptance

Design succeeds when independent operator can register tasks, import manually generated solutions, execute hidden evaluation, produce run-level metrics, and generate condition-level effect estimates without editing study code. Repeated analysis of same inputs must produce identical outputs.
