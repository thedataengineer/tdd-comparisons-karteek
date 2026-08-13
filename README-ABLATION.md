# TDD Ablation Toolkit

Command-line toolkit for registering manually generated coding runs, evaluating them against hidden tests, mutmut 3.6.0 mutation scoring, inter-rater reliability calibration, and estimating quality and cost effects across 8 engineering-process conditions.

Read [methodology update](study/methodology-update.md) for comparison with initial TDD experiment, statistical basis, adoption criteria, and current evidence status.

## Usage

```bash
# Validate study setup
tdd-ablation validate --study study

# Generate randomized run schedule
tdd-ablation schedule --phase screening --study study --output study/screening/schedule.csv

# Verify store integrity
tdd-ablation verify-store --study study

# Generate executive report
tdd-ablation report --study study --output study/reports
```
