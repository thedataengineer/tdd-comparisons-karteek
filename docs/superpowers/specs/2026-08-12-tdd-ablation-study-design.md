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

Each hypothesis must define metric, effect direction, minimum useful effect, sample size, and analysis rule before first run. [ASSUMPTION] Initial adoption threshold requires five percentage points higher severity-weighted hidden-test score without higher severe-defect incidence.

Pre-registration includes power analysis for every confirmatory hypothesis. Analysis states baseline rate and variance assumptions, minimum detectable effect, alpha, target power, expected run attrition, task-level clustering, repeated-run structure, planned statistical model, and executable calculation. Use two-sided alpha 0.05 and at least 80 percent power unless pre-registration states stricter values. Final sample size equals larger of protocol minimum and power-analysis result; no observed screening effect may reduce it.

## Experimental Conditions

Screening compares eight conditions:

1. Task only
2. Tests required, timing unspecified
3. Tests written after implementation
4. Tests written first as batch
5. Incremental red-green cycles
6a. Incremental red-green cycles with upfront contract design
6b. Incremental red-green cycles with mandatory refactoring checkpoints
6c. Incremental red-green cycles with upfront contract design and mandatory refactoring checkpoints

All conditions receive identical task specification, environment, dependencies, completion budget, and tool permissions. Only process instruction changes. Conditions never include coverage targets because coverage requirements would confound testing practice with completion policy.

## Task Portfolio

Screening uses 12 tasks across parsing, state transitions, concurrency, API contracts, transformations, and defect repair. Tasks contain similar difficulty bands but different domain wording and implementation details.

Each task includes public requirements, hidden acceptance tests, adversarial cases, severity labels, and mutation configuration. Task author freezes hidden evaluation before any coding run begins.

## Run Protocol

Run every task-condition cell at least six times during screening. Randomize execution order. Create fresh isolated workspace for every run and never reuse generated code across conditions. Eight conditions, 12 tasks, and six repetitions produce minimum 576 screening runs before any increase required by power analysis.

Pin model identifier, model settings, tool permissions, timeout, runtime, dependency versions, and hardware class. Before main study, run separate budget pilot excluded from study results. Set one shared token ceiling at largest condition-specific pilot observed maximum plus 20 percent margin, subject to provider context limit; feasible pilot sizes make nearest-rank 95th percentile equal the maximum, so the rule names the maximum explicitly. Set one shared timeout from the same maximum-plus-margin rule, subject to runtime cap. Freeze ceiling for all conditions. Never grant condition-specific extensions. Primary intention-to-treat analysis scores budget-exhausted and timed-out runs as incomplete outcomes; secondary analysis reports uncensored completed runs. Report censoring rate by condition and stop study for protocol review if any condition exceeds 10 percent censoring.

Create three semantically equivalent prompt variants per condition. Variants preserve same obligations, prohibitions, completion criteria, and information while changing wording and order. Freeze and hash variants before first run. Allocate two screening repetitions per task to each variant, randomize variant within condition, and include prompt variant plus condition-by-variant interaction in analysis. Confirmation uses four paired repetitions per variant. Material interaction blocks broad condition claim until replication with revised prompt set.

Record failed and timed-out runs instead of silently replacing them. Replacement runs receive separate identifiers and remain linked to original failures.

Store immutable run manifest containing condition ID, task ID, repetition, randomized order, model configuration, prompt hashes, source commit, timestamps, token counts, tool calls, exit state, and artifact hashes.

## Evaluation

Coding agent cannot access hidden evaluation artifacts. Deterministic checks provide primary evidence:

- Hidden functional tests
- Adversarial boundary tests
- Mutation testing against submitted tests using Python 3.12 and `mutmut==3.6.0`
- API and dependency conformance checks
- Static checks for dead code and forbidden dependencies
- Human adjudication for disputed high-severity failures

Hidden-test severity uses frozen four-level rubric: critical for security, irreversible corruption, or contract-wide failure; high for crash, wrong state transition, or materially incorrect result; medium for bounded incorrect behavior with workaround; low for presentation or maintainability defect without incorrect domain result. Two domain reviewers independently label each hidden test before first coding run. Reviewers calibrate against 10 seeded defects, require weighted Cohen's kappa of at least 0.80, adjudicate disagreements, and freeze final labels and weights. Report original labels, agreement, adjudication changes, and mapping from tests to affected business behavior.

Blind design review removes condition labels, prompt text, session traces, and naming clues. Two reviewers score each artifact independently against frozen rubric. Report weighted Cohen's kappa for two reviewers or Krippendorff's alpha for larger panels, using 0.70 as minimum acceptable reliability. Scores below threshold trigger rubric recalibration and full independent rescoring before unblinding. Adjudicated score remains secondary; analysis also reports original reviewer scores and agreement interval. Model-based review remains secondary evidence. Generator and model judge cannot share identical model configuration for primary scoring.

Mutation protocol pins Python 3.12 patch release, `mutmut==3.6.0`, submitted test command, source paths, test timeout, per-mutant timeout multiplier, worker count, and environment variables in task manifest. Use full default mutmut 3.6.0 operator set without operator filtering. Preserve mutant ID, source location, generated diff, operator classification, test result, duration, and timeout state. Denominator includes killed, survived, suspicious, and timed-out mutants; import or collection failures invalidate run. Two reviewers independently classify suspected equivalent mutants while blind to condition, and primary score retains them in denominator. Sensitivity analysis reports score excluding adjudicated equivalents. Never hand-select mutants after seeing condition results.

Primary metric: severity-weighted hidden-test score. Secondary metrics include high-severity defect count, mutation score, authored-test effectiveness, tokens, elapsed time, tool calls, human review minutes, and implementation-to-test LOC ratio. Line coverage remains diagnostic data.

## Analysis

Analyze practice effects by task and across task families. Report effect sizes and confidence intervals, not rank alone. Treat each unique generation run as one observation; copied artifacts never count again.

Ablation interpretation:

- Testing need exists when tests-required condition beats task-only condition.
- Test-first need exists when batched test-first beats tests-after.
- Incremental-cycle need exists when red-green beats batched test-first enough to cover added cost.
- Contract design earns confirmation when condition 6a beats condition five.
- Refactoring checkpoints earn confirmation when condition 6b beats condition five.
- Combined practice earns confirmation when condition 6c beats condition five and exceeds both 6a and 6b by pre-registered margin.
- Metric validity exists when metric predicts hidden correctness on unseen runs.

Confirmation uses 12 unseen tasks and 12 paired repetitions per task-condition cell, balanced as four repetitions per prompt variant. Each promoted practice runs against its pre-registered matched baseline. Power analysis may increase but never reduce 144 runs per condition. Confirmation succeeds only when 95 percent confidence interval for mean severity-weighted hidden-test difference excludes zero, point estimate reaches at least five percentage points, and upper 95 percent confidence bound for severe-defect risk ratio stays below 1.10. Economic adoption also requires positive lower confidence bound for expected value under pre-registered cost assumptions. Any failed criterion rejects adoption claim.

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

Results apply only to pinned model identifier and version. Study makes no cross-version claim. Model-version sensitivity requires separate registered replication using unchanged tasks, prompts, budgets, and scoring; this replication sits outside first release. Any provider model update during active phase pauses new runs until operator either restores pinned version or starts separate version stratum.

## Acceptance

Design succeeds when independent operator can register tasks, import manually generated solutions, execute hidden evaluation, produce run-level metrics, and generate condition-level effect estimates without editing study code. Repeated analysis of same inputs must produce identical outputs.
